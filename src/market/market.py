from multiprocessing import Process
from multiprocessing.managers import SyncManager
import threading
import transaction_handler as th
import socket
import select
import concurrent.futures
import price
from external import ExternalEvent
import signal
import sys
import time
sys.path.append('../')

from constants import *

MAX_THREADS = 10

external = False

def signal_handler(sig, frame):
    global external
    if sig == signal.SIGUSR1:
        external = not external
        print(external)

signal.signal(signal.SIGUSR1, signal_handler)

class DictManager(SyncManager): pass

class Market(Process):
    def __init__(self):
        super().__init__()

    def create_connections(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((HOST, PORT))
            server_socket.listen()
            server_socket.setblocking(False)

            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                while True:
                    readable, writable, error = select.select([server_socket], [], [], 1)
                    if server_socket in readable:
                        client_socket, address = server_socket.accept()
                        executor.submit(th.transaction_handler, client_socket, address)

    def get_weather(self):
        DictManager.register('weather_updates')
        m = DictManager(address=('', SHARED_MEMORY_PORT), authkey=SHARED_MEMORY_KEY)
        m.connect()
        weather_updates = m.weather_updates()
        
        return weather_updates

    def calculate_price(self):
        pass
    
    def run(self):
        ex_event_process = ExternalEvent()
        ex_event_process.start()

        create_connections_thread = threading.Thread(target=self.create_connections)
        create_connections_thread.start()

        weather_updates = self.get_weather()
        previous_price = STD_PRICE
        while True:
            time.sleep(1)
            temperature = weather_updates.get("temp")
            new_price = 0.99 * previous_price + 0.001 * (1 / temperature) + 0.01 * external
            price.setPrice(new_price)
            previous_price = new_price
            print(price.price)

if __name__ == "__main__":
    price.setPrice(STD_PRICE)
    market_process = Market()

    market_process.start()
    market_process.join()

    pass