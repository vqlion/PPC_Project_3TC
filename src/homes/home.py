from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
import socket
import time
import threading
import numpy as np
import os
import sys

sys.path.append('../')
from constants import *

class DictManager(SyncManager): pass

class Home(Process):
    def __init__(self, initial_balance, initial_energy, give_queue, ask_queue, strategy):
        super().__init__()
        self.balance = initial_balance
        self.energy = initial_energy
        self.give_queue = give_queue
        self.ask_queue = ask_queue
        self.energy_prod = STD_ENERGY
        self.energy_cons = STD_ENERGY
        self.strategy = strategy

    def transaction_handler(self, operation, value, balance_mutex):
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
                        with balance_mutex:
                            self.balance -= float(message_received[1])
                    elif operation == 'sell':
                        with balance_mutex:
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
            # time.sleep(1)
            energy_produced = np.random.normal(loc=self.energy_prod, scale=0.5, size=1)[0]
            with energy_mutex:
                self.energy += energy_produced
            if self.strategy == 1:
                self.give_queue.put()

    def consume_energy(self, energy_mutex):
        while True:
            # time.sleep(1)
            energy_consumed = np.random.normal(loc=self.energy_cons, scale=0.5, size=1)[0]
            with energy_mutex:
                self.energy -= energy_consumed

    def run(self):
        weather_updates = self.get_weather()
        energy_mutex = threading.Lock()
        balance_mutex = threading.Lock()

        self.transaction_handler('sell', 0.25, balance_mutex)

        consumer_thread = threading.Thread(target=self.consume_energy, args=(energy_mutex, )).start()
        producer_thread = threading.Thread(target=self.produce_energy, args=(energy_mutex, )).start()
        while True:
            print(os.getpid(), "cons", self.energy_cons, "prod", self.energy_prod, "energy", self.energy)
            temperature =  weather_updates.get("temp")
            temperature_deviance = STD_TEMP - temperature
            self.energy_cons = STD_ENERGY + 0.5 * temperature_deviance
