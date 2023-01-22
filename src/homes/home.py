from multiprocessing import Process
import socket

HOST = "localhost"
PORT = 1515

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
                    current_price = int(message_received[1])
                    if operation == 'buy' and current_price * value > self.balance:
                        client_socket.sendall('end'.encode())
                        return 1
                    res = f'{operation} {value}'
                    client_socket.sendall(res.encode())
                
                elif message_received[0] == f'ok_{operation}':
                    if operation == 'buy':
                        self.balance -= int(message_received[1])
                    elif operation == 'sell':
                        self.balance += int(message_received[1])
                    client_socket.sendall('end'.encode())
                    return 0

            return 1


    def run(self):
        self.transaction_handler('sell', 10)
        print(self.balance)
        pass