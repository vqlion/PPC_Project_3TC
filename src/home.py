from src.constants import *
from multiprocessing import Process
from multiprocessing.managers import SyncManager
import socket
import time
import threading
import numpy as np
import signal
import sysv_ipc

stop_event = threading.Event()
NEEDY_LIMIT = 10

def handler_alrm(sig, frame):
    #Home will cease activity upon receiving signal to terminate
    global stop_event
    if sig == signal.SIGALRM:
        stop_event.set()


class DictManager(SyncManager): #shared memory related
    pass

class bcolors: #the prints can have colors!
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = "\033[1;31m"
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = "\033[0;0m"
 

class Home(Process):
    #Each home is a process represented by an instance of this class, called by the home creator script 
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
        self.needy = True #needy is true when the home is under NEEDY_LIMIT energy
        self.idle = False #idle is true when the home is out of energy
        self.id = id

    def transaction_handler(self, operation, value):
        #handles transactions with the market. operation is the transaction type, value is the amount of energy bought/sold
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
                        return 1 #return 1 when the operation didn't go through

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
                    return 0 #return 0 when the operation went through

    def get_weather(self):
        #returns the weather dictionary (shared memory)
        DictManager.register('weather_updates')
        m = DictManager(address=('', SHARED_MEMORY_PORT),
                        authkey=SHARED_MEMORY_KEY)

        m.connect()
        weather_updates = m.weather_updates()

        return weather_updates

    def produce_energy(self):
        #separate thread that handles the production
        global stop_event
        while not stop_event.is_set():
            if not self.idle:
                time.sleep(1) #energy is produced every second to avoid instant convergence
                energy_produced = np.random.normal(
                    loc=self.energy_prod, scale=0.5, size=1)[0]
                #the amount of energy produced is defined by a normal distribution around the production value
                #just to make things more interesting...

                if self.needy: #keep the energy if needed
                    with self.energy_mutex:
                        self.energy += energy_produced

                else: #give the energy based on the strategy
                    if self.strategy == 1:
                        self.queue.send(str(energy_produced).encode(), type=1)
                        print(bcolors.OKBLUE + f"Home {self.id} gave {energy_produced} to the community." + bcolors.RESET)

                    elif self.strategy == 2:
                        self.transaction_handler('sell', energy_produced)
                        print(bcolors.OKBLUE + f"Home {self.id} sold {energy_produced} to the market." + bcolors.RESET)

                    else:
                        try:
                            self.queue.receive(block=False, type=2)
                            self.queue.send(str(energy_produced).encode(), type=1)
                            print(bcolors.OKBLUE + f"Home {self.id} gave {energy_produced} to the community." + bcolors.RESET)
                        except:
                            self.transaction_handler('sell', energy_produced)
                            print(bcolors.OKBLUE + f"Home {self.id} sold {energy_produced} to the market." + bcolors.RESET)

    def consume_energy(self):
        #separate thread that handle the consumption
        global stop_event
        while not stop_event.is_set():
            if not self.idle:
                time.sleep(1) #every second to avoid instant convergence
                energy_consumed = np.random.normal(
                    loc=self.energy_cons, scale=0.5, size=1)[0]
                #same as energy produced

                with self.energy_mutex:
                    if self.energy > energy_consumed:
                        self.energy -= energy_consumed

                    else:
                        self.energy = 0
                        self.idle = True

    def handle_energy(self):
        #separate thrad to handle energy crisis (home running out)
        global stop_event
        while not stop_event.is_set():
            if self.idle:
                self.send_update()
                print(bcolors.RED + f"Home {self.id} out of energy. It goes idle." + bcolors.RESET)

                if self.transaction_handler('buy', 3): #tries to buy energy and check whether it worked
                    energy_taken = ""
                    try:
                        energy_taken, t = self.queue.receive(block=False, type=1) #try to get energy from the queue
                    except:
                        self.queue.send(1, type=2) #if it didn't work, ask the queue
                        energy_taken, t = self.queue.receive(type=1)
                    energy_taken = float(energy_taken.decode())

                    with self.energy_mutex:
                        self.energy += energy_taken

                    print(bcolors.OKGREEN + f"Home {self.id} out of idle: took {energy_taken} from the community." + bcolors.RESET)
                else:
                    with self.energy_mutex:
                        self.energy += 3

                    print(bcolors.OKGREEN + f"Home {self.id} got out of idle: bought 3 from the market." + bcolors.RESET)

                self.idle = False

    def update_logs(self):
        #separate thread to update the main process with the current state of things
        global stop_event
        while not stop_event.is_set():
            time.sleep(1)
            self.send_update()

    def send_update(self):
        #sends a message to the main process
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, MAIN_PORT))
            message = f"home {self.id} {self.balance} {self.energy if not self.idle else 0}"
            client_socket.sendall(message.encode())


    def run(self):
        print(f"Home {self.id + 1} is starting...")
        global stop_event
        weather_updates = self.get_weather()
        signal.signal(signal.SIGALRM, handler_alrm) #attach the signal.SIGALARM signals to the handler

        consumer_thread = threading.Thread(target=self.consume_energy)
        consumer_thread.start()

        producer_thread = threading.Thread(target=self.produce_energy)
        producer_thread.start()

        handler_thread = threading.Thread(target=self.handle_energy)
        handler_thread.start()

        update_thread = threading.Thread(target=self.update_logs)
        update_thread.start()

        while not stop_event.is_set():
            temperature = weather_updates.get("temp")
            self.energy_cons = STD_ENERGY + (1 / temperature)
            self.needy = True if self.energy < NEEDY_LIMIT else False
        
        consumer_thread.join()
        producer_thread.join()
        handler_thread.join()
        update_thread.join()
        
        print(f"Home {self.id + 1} is terminating...")
