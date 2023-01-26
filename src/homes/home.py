import sys
sys.path.append('../')
from constants import *
from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
import socket
import time
import threading
import numpy as np
import os


class DictManager(SyncManager):
    pass


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
        self.energy_mutex = threading.Lock()
        self.balance_mutex = threading.Lock()
        self.needy = True
        self.idle = False

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
                        with self.balance_mutex:
                            self.balance -= float(message_received[1])
                    elif operation == 'sell':
                        with self.balance_mutex:
                            self.balance += float(message_received[1])
                    client_socket.sendall('end'.encode())
                    return 0

    def get_weather(self):
        DictManager.register('weather_updates')
        m = DictManager(address=('', SHARED_MEMORY_PORT),
                        authkey=SHARED_MEMORY_KEY)
        m.connect()
        weather_updates = m.weather_updates()

        return weather_updates

    def produce_energy(self):
        while True:
            if not self.idle:
                time.sleep(1)
                energy_produced = np.random.normal(
                    loc=self.energy_prod, scale=0.5, size=1)[0]

                if self.needy:
                    with self.energy_mutex:
                        self.energy += energy_produced
                else:
                    if self.strategy == 1:
                        self.give_queue.put(energy_produced)
                    elif self.strategy == 2:
                        self.transaction_handler('sell', energy_produced)
                    else:
                        try:
                            self.ask_queue.get(block=True, timeout=0.1)
                            self.give_queue.put(energy_produced)
                        except:
                            self.transaction_handler('sell', energy_produced)

    def consume_energy(self):
        while True:
            if not self.idle:
                time.sleep(1)
                energy_consumed = np.random.normal(
                    loc=self.energy_cons, scale=0.5, size=1)[0]

                with self.energy_mutex:
                    if self.energy > energy_consumed:
                        self.energy -= energy_consumed
                    else:
                        self.energy = 0
                        self.idle = True

    def handle_energy(self):
        while True:
            if self.idle:
                print(os.getpid(), "went idle!")
                if self.transaction_handler('buy', 10):
                    energy_taken = 0
                    try:
                        energy_taken = self.give_queue.get(block=True, timeout=0.1)
                    except:
                        self.ask_queue.put(1)
                        energy_taken = self.give_queue.get()

                    with self.energy_mutex:
                        self.energy += energy_taken
                    print(os.getpid(), "got out of idle : take")
                else:
                    print(os.getpid(), "got out of idle : buy")
                    with self.energy_mutex:
                        self.energy += 10
                self.idle = False

    def printer(self):
        while True:
            time.sleep(1)
            print(os.getpid(), "cons", self.energy_cons, "prod",
                self.energy_prod, "energy", self.energy, "balance", self.balance)

    def run(self):
        print(os.getpid(), "cons", self.energy_cons, "prod",
              self.energy_prod, "energy", self.energy, "balance", self.balance)
        weather_updates = self.get_weather()

        printer = threading.Thread(target=self.printer).start()
        consumer_thread = threading.Thread(target=self.consume_energy).start()
        producer_thread = threading.Thread(target=self.produce_energy).start()
        handler_thread = threading.Thread(target=self.handle_energy).start()
        while True:
            temperature = weather_updates.get("temp")
            self.energy_cons = STD_ENERGY + 0.5 * (1 / temperature)
            self.needy = True if self.energy < 10 else False
