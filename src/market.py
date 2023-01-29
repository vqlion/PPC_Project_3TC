from multiprocessing import Process
from multiprocessing.managers import SyncManager
from concurrent.futures import ThreadPoolExecutor
import threading
from src import transaction_handler as th
import socket
import select
from src import price
import signal
import time
from src.constants import *
import random
import os

MAX_THREADS = 10

external_event = False
big_external_event = False
stop_event = threading.Event()

def signal_handler(sig, frame):
    global external_event
    global big_external_event
    if sig == signal.SIGUSR1:
        if big_external_event:
            big_external_event = False
        else:
            external_event = not external_event
    elif sig == signal.SIGUSR2:
        big_external_event = True

signal.signal(signal.SIGUSR1, signal_handler)
signal.signal(signal.SIGUSR2, signal_handler)

def handler_alrm(sig, frame):
    global stop_event
    if sig == signal.SIGALRM:
        stop_event.set()

def create_external_events():
    global stop_event
    while not stop_event.is_set():
        time.sleep(1)
        decider = random.random()
        if decider < 0.1:
            if decider > 0.01:
                os.kill(os.getppid(), signal.SIGUSR1)
            else:
                os.kill(os.getppid(), signal.SIGUSR2)
        
class DictManager(SyncManager): pass

def create_connections():
    global stop_event
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, MARKET_PORT))
        server_socket.listen()
        server_socket.setblocking(False)

        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            while not stop_event.is_set():
                readable, writable, error = select.select([server_socket], [], [], 1)
                if server_socket in readable:
                    client_socket, address = server_socket.accept()
                    executor.submit(th.transaction_handler, client_socket, address)

        server_socket.close()

def get_weather():
    DictManager.register('weather_updates')
    m = DictManager(address=('', SHARED_MEMORY_PORT), authkey=SHARED_MEMORY_KEY)
    m.connect()
    weather_updates = m.weather_updates()
    
    return weather_updates

def update_logs():
    global stop_event, external_event, big_external_event
    while not stop_event.is_set():
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, MAIN_PORT))
            event_value = 0
            if external_event: event_value = 1
            if big_external_event: event_value = 2
            message = f"market 0 {price.price} {event_value}"
            client_socket.sendall(message.encode())

def market():
    price.setPrice(STD_PRICE)
    global stop_event
    ex_event_process = Process(target=create_external_events, daemon=True)
    ex_event_process.start()

    create_connections_thread = threading.Thread(target=create_connections)
    
    create_connections_thread.start()

    update_thread = threading.Thread(target=update_logs)
    update_thread.start()

    weather_updates = get_weather()
    previous_price = STD_PRICE
    signal.signal(signal.SIGALRM, handler_alrm)
    while not stop_event.is_set():
        time.sleep(1)
        temperature = weather_updates.get("temp")
        current_cons = STD_ENERGY + (1 / temperature)
        new_price = (0.99 * previous_price) + (0.001 * (1 / temperature)) + (0.01 * external_event) + big_external_event + (0.0001 * current_cons)
        price.setPrice(new_price)
        previous_price = new_price

    create_connections_thread.join()
    update_thread.join()
    print('The market process is terminating...')