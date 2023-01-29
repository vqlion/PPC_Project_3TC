import threading
from multiprocessing.managers import SyncManager
import numpy as np
import time
from src.constants import *
import signal
import os
import socket

server = None

class DictManager(SyncManager): pass

stop_event = threading.Event()

def handler_alrm(sig, frame):
    global stop_event
    if sig == signal.SIGALRM:
        stop_event.set()


weather_updates = {}
def get_dict():
    return weather_updates

def weather_server():
    global server
    DictManager.register('weather_updates', get_dict)
    m = DictManager(address=('', SHARED_MEMORY_PORT), authkey=SHARED_MEMORY_KEY)
    server = m.get_server()
    server.serve_forever()

def stop_weather_server():
    global server
    server.stop_event.set()

def update_logs():
    global stop_event
    while not stop_event.is_set():
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, MAIN_PORT))
            message = f"weather 0 {weather_updates.get('temp')} 0"
            client_socket.sendall(message.encode())

def create_weather():
    global stop_event
    server_thread = threading.Thread(target=weather_server)
    server_thread.start()
    weather_updates.update(([('temp', STD_TEMP)]))
    signal.signal(signal.SIGALRM, handler_alrm)

    update_thread = threading.Thread(target=update_logs)
    update_thread.start()

    while not stop_event.is_set():
        temp = weather_updates.get('temp')
        new_temp = temp + np.random.normal(loc=0, scale=0.25, size=1)[0] 
        time.sleep(1)
        weather_updates.update(([('temp', new_temp)]))

    stop_weather_server()
    server_thread.join()
    update_thread.join()
    print("The weather process is terminating...")