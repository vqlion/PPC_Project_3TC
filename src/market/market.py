from multiprocessing import Process
import transaction_handler as th
import socket
import select
import concurrent.futures
import price
from external import ExternalEvent
import signal

HOST = "localhost"
PORT = 1515
MAX_THREADS = 10

external = False

def signal_handler(sig, frame):
    global external
    if sig == signal.SIGUSR1:
        external = not external
        print(external)

signal.signal(signal.SIGUSR1, signal_handler)

class Market(Process):
    def __init__(self):
        super().__init__()

    def run(self):
        ex_event_process = ExternalEvent()
        ex_event_process.start()
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


if __name__ == "__main__":
    price.setPrice(1000)
    market_process = Market()

    market_process.start()
    market_process.join()

    pass