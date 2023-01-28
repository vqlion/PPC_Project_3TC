from src.constants import *
from multiprocessing import Process
from multiprocessing.managers import SyncManager
import socket
import time
import threading
import numpy as np
import os
import signal
import sysv_ipc

stop_event = threading.Event()

def handler_alrm(sig, frame):
    global stop_event
    if sig == signal.SIGALRM:
        print("home received signal to terminate")
        stop_event.set()


class DictManager(SyncManager):
    pass

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
 

class Home(Process):
    def __init__(self, initial_balance, initial_energy, strategy, id):
        super().__init__()
        self.balance = initial_balance
        self.energy = initial_energy
        self.queue = sysv_ipc.MessageQueue(MESSAGE_QUEUE_KEY)
        self.energy_prod = STD_ENERGY
        self.energy_cons = STD_ENERGY
        self.strategy = strategy
        self.energy_mutex = threading.Lock()
        self.balance_mutex = threading.Lock()
        self.needy = True
        self.idle = False
        self.id = id

    def transaction_handler(self, operation, value):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, MARKET_PORT))
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
        global stop_event
        while not stop_event.is_set():
            if not self.idle:
                time.sleep(1)
                energy_produced = np.random.normal(
                    loc=self.energy_prod, scale=0.5, size=1)[0]

                if self.needy:
                    with self.energy_mutex:
                        self.energy += energy_produced
                else:
                    if self.strategy == 1:
                        self.queue.send(str(energy_produced).encode(), type=1)
                        print(bcolors.OKBLUE + f"Home {self.id} gave {energy_produced} to the queue")
                    elif self.strategy == 2:
                        self.transaction_handler('sell', energy_produced)
                    else:
                        try:
                            self.queue.receive(block=False, type=2)
                            self.queue.send(str(energy_produced).encode(), type=1)
                        except:
                            self.transaction_handler('sell', energy_produced)

    def consume_energy(self):
        global stop_event
        while not stop_event.is_set():
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
        global stop_event
        while not stop_event.is_set():
            if self.idle:
                print(bcolors.FAIL + f"Home {self.id} is out of energy. It goes idle with a balance of {self.balance}")
                if self.transaction_handler('buy', 3):
                    energy_taken = ""
                    try:
                        energy_taken, t = self.queue.receive(block=False, type=1)
                    except:
                        self.queue.send(1, type=2)
                        energy_taken, t = self.queue.receive(type=1)
                    energy_taken = float(energy_taken.decode())
                    with self.energy_mutex:
                        self.energy += energy_taken
                    print(bcolors.OKCYAN + f"Home {self.id} got out of idle: took {energy_taken} from the queue. Current amount of energy: {self.energy}")
                else:
                    with self.energy_mutex:
                        self.energy += 3
                    print(bcolors.OKGREEN + f"Home {self.id} got out of idle: bought 3 from the market. . Current amount of energy: {self.energy}. New balance is {self.balance}")
                self.idle = False

    def run(self):
        global stop_event
        print(os.getpid(), self.id)
        weather_updates = self.get_weather()
        signal.signal(signal.SIGALRM, handler_alrm)

        consumer_thread = threading.Thread(target=self.consume_energy)
        consumer_thread.start()
        producer_thread = threading.Thread(target=self.produce_energy)
        producer_thread.start()
        handler_thread = threading.Thread(target=self.handle_energy)
        handler_thread.start()
        while not stop_event.is_set():
            temperature = weather_updates.get("temp")
            self.energy_cons = STD_ENERGY + (1 / temperature)
            self.needy = True if self.energy < 10 else False
        
        consumer_thread.join()
        producer_thread.join()
        handler_thread.join()
