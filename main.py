import socket
import select
import concurrent.futures
import sys
import time
from multiprocessing import Process
import json
import os
import signal

from src import home_creator
from src import market
from src import weather
from src import constants

MAX_THREADS = 5

homes_data = []
market_data = {}
weather_data = {}


def create_connections():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((constants.HOST, constants.MAIN_PORT))
        server_socket.listen()
        server_socket.setblocking(False)

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            while True:
                readable, writable, error = select.select(
                    [server_socket], [], [], 1)
                if server_socket in readable:
                    client_socket, address = server_socket.accept()
                    executor.submit(transaction_handler,
                                    client_socket, address)


def transaction_handler(socket, address):
    with socket as client_socket:
        data = client_socket.recv(1024)
        message = data.decoded().split()


if __name__ == "__main__":
    if len(sys.argv) != 2:  # Check number of arguments is correct
        print("Provide one argument: the number of homes")
        sys.exit(0)

    try:  # handling type errors (user doesn't input a number)
        int(sys.argv[1])
    except Exception as e:
        print("Provide an integer as the parameter for the number of homes")
        sys.exit(0)

    number_of_homes = int(sys.argv[1])

    if (number_of_homes < 0):
        print('Provide a positive integer!')
        sys.exit(0)

    for i in range(number_of_homes):
        homes_data.append({"id": i})

    weather_process = Process(target=weather.create_weather)
    market_process = Process(target=market.market)
    homes_process = Process(target=home_creator.create_homes, args=(number_of_homes, ))

    print("starting weather")
    weather_process.start()
    time.sleep(1)
    print("starting market")
    market_process.start()
    time.sleep(1)
    print("starting homes")
    homes_process.start()

    input("Type anything to stop.")

    os.kill(weather_process.pid, signal.SIGALRM)
    os.kill(market_process.pid, signal.SIGALRM)
    os.kill(homes_process.pid, signal.SIGALRM)


    print('i reached the end of main')

with open('homes_data.json', 'w') as json_file:
    json.dump(homes_data, json_file,
              indent=4,
              separators=(',', ': '))