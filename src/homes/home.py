from multiprocessing import Process
from multiprocessing.managers import SyncManager
import socket
import time
import threading
import numpy as np
import os

HOST = "localhost"
PORT = 1515
SHARED_MEMORY_KEY = b'Dinosour'
SHARED_MEMORY_PORT = 54545

STD_ENERGY = 7
ENERGY_PROD = 7
ENERGY_CONS = 7
STD_TEMP = 15

class DictManager(SyncManager): pass

class Home(Process):
    def __init__(self, initial_balance, initial_energy):
        super().__init__()
        self.balance = initial_balance
        self.energy = initial_energy

    def transaction_handler(self, operation, value):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, PORT))
            message_received = ['']
            client_socket.sendall('price?'.encode())
            current_price = 0

            while message_received[0] != 'end' and message_received[0] != 'invalid':
                data = client_socket.recv(1024)
                message_received = data.decode().split()

                if message_received[0] == 'price':
                    current_price = float(message_received[1])
                    if operation == 'buy' and current_price * value > self.balance:
                        client_socket.sendall('end'.encode())
                        return 1
                    res = f'{operation} {value}'
                    client_socket.sendall(res.encode())
                
                elif message_received[0] == f'ok_{operation}':
                    if operation == 'buy':
                        self.balance -= float(message_received[1])
                    elif operation == 'sell':
                        self.balance += float(message_received[1])
                    client_socket.sendall('end'.encode())
                    return 0

            return 1

    def get_weather(self):
        DictManager.register('weather_updates')
        m = DictManager(address=('', SHARED_MEMORY_PORT), authkey=SHARED_MEMORY_KEY)
        m.connect()
        weather_updates = m.weather_updates()
        
        return weather_updates
    
    def produce_energy(self, energy_mutex):
        while True:
            time.sleep(1)
            energy_produced = np.random.normal(loc=ENERGY_PROD, scale=0.5, size=1)[0]
            with energy_mutex:
                self.energy += energy_produced

    def consume_energy(self, energy_mutex):
        while True:
            time.sleep(1)
            energy_consumed = np.random.normal(loc=ENERGY_CONS, scale=0.5, size=1)[0]
            with energy_mutex:
                self.energy -= energy_consumed
            print(os.getpid(), "cons", ENERGY_CONS, "energy", self.energy)

    def run(self):
        global ENERGY_CONS, ENERGY_PROD
        # self.transaction_handler('sell', 0.25)
        w_update = self.get_weather()
        energy_mutex = threading.Lock()

        producer_thread = threading.Thread(target=self.produce_energy, args=(energy_mutex, )).start()
        consumer_thread = threading.Thread(target=self.consume_energy, args=(energy_mutex, )).start()
        while True:
            temperature =  w_update.get("temp")
            temperature_deviance = STD_TEMP - temperature
            ENERGY_CONS = STD_ENERGY + 0.5 * temperature_deviance
