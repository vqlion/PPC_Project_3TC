import threading
from multiprocessing.managers import SyncManager
import numpy as np
import time
from src.constants import *
import signal
import socket

server = None

class DictManager(SyncManager): pass

stop_event = threading.Event()
weather_updates = {}

def handler_alrm(sig, frame):
    #the process stops its activities upon receiving termination signal
    global stop_event
    if sig == signal.SIGALRM:
        stop_event.set()

def get_dict():
    return weather_updates

def weather_server():
    #initialize and start the shared memory
    global server
    DictManager.register('weather_updates', get_dict)
    m = DictManager(address=('', SHARED_MEMORY_PORT), authkey=SHARED_MEMORY_KEY)
    server = m.get_server()
    server.serve_forever()

def stop_weather_server():
    #stop the shared memory
    global server
    server.stop_event.set()

def update_logs():
    #updates the main process every second
    global stop_event
    while not stop_event.is_set():
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, MAIN_PORT))
            raining = weather_updates.get('rain')
            message = f"weather 0 {weather_updates.get('temp')} {0 if not raining else 1}"
            client_socket.sendall(message.encode())

def create_weather():
    global stop_event

    server_thread = threading.Thread(target=weather_server)
    server_thread.start()

    update_thread = threading.Thread(target=update_logs)
    update_thread.start()

    raining = False

    weather_updates.update([('temp', STD_TEMP), ('rain', raining)])

    signal.signal(signal.SIGALRM, handler_alrm)

    cycles = 0
    while not stop_event.is_set():
        temp = weather_updates.get('temp')
        new_temp = temp + np.random.normal(loc=0, scale=0.25, size=1)[0] 
        #the temperature is updated every second based on a normal distribution centered arount the previous temperature
        #this just makes the graph look better 
        if np.random.rand() < 0.75 and cycles >= 3:
            raining = False
        elif not raining:
            raining = True
            cycles = 0
        time.sleep(1)
        weather_updates.update([('temp', new_temp), ('rain', raining)])
        cycles += 1
        

    stop_weather_server()
    server_thread.join()
    update_thread.join()
    
    print("The weather process is terminating...")