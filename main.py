import socket
import select
import concurrent.futures
import sys
import time
from multiprocessing import Process
import json
import os
import signal
import threading
import sysv_ipc

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
import numpy as np

from src import home_creator
from src import market
from src import weather
from src import constants

MAX_THREADS = 5

homes_data = []
market_data = []
weather_data = []

homes_mutex = threading.Lock()
stop_event = threading.Event()

startup_time = 0

def create_connections():
    global stop_event
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((constants.HOST, constants.MAIN_PORT))
        server_socket.listen()
        server_socket.setblocking(False)

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            while not stop_event.is_set():
                readable, writable, error = select.select(
                    [server_socket], [], [], 1)
                if server_socket in readable and not stop_event.is_set():
                    client_socket, address = server_socket.accept()
                    executor.submit(transaction_handler,
                                    client_socket, address)


def transaction_handler(socket, address):
    global homes_data, market_data, weather_data, startup_time
    with socket as client_socket:
        data = client_socket.recv(1024)
        message = data.decode().split()

        source = message[0]
        id = int(message[1])
        info1 = float(message[2])
        info2 = float(message[3])
        current_time = time.time()
        time_since_beginning = current_time - startup_time

        if source == "market":
            market_data.append({"time": time_since_beginning, "price": info1, "event": info2})
        elif source == "weather":
            weather_data.append({"time": time_since_beginning, "temp": info1})
        elif source == "home":
            with homes_mutex:
                homes_data[id]["log"].append({"time": time_since_beginning, "balance": info1, "energy": info2})

fig, ax = plt.subplots(2, 2)
plt.suptitle("Visual representation of the simulation. Close the window to end.", fontsize="large")
width = 0.35


def plotter(i):
    for row in ax:
        for col in row:
            col.clear()

    ax[0, 0].plot([d["time"] for d in market_data], [d["price"] for d in market_data], 'b')
    ax[1, 1].plot([d["time"] for d in weather_data], [d["temp"] for d in weather_data], 'r')
    ax[1, 0].plot([d["time"] for d in market_data], [d["event"] for d in market_data], 'g')

    x = np.arange(len(homes_data))
    balances = []
    energies = []
    labels = []
    i = 0

    for home in homes_data:
        balance_list = [d["balance"] for d in home["log"]]
        energy_list = [d["energy"] for d in home["log"]]

        current_balance = balance_list[-1]
        current_energy = energy_list[-1]

        balances.append(current_balance)
        energies.append(current_energy)
        labels.append(f'Home {i+1}')
        i += 1

    balance_bar = ax[0, 1].bar(x - width / 2, balances, width, label='Balance (euros)', color='b')
    energy_bar = ax[0, 1].bar(x + width / 2, energies, width, label='Energy (kWh)', color='r')
    ax[0, 1].bar_label(balance_bar, padding=3)
    ax[0, 1].bar_label(energy_bar, padding=3)

    patches = [[None for _ in range(2)] for _ in range(2)]

    patches[0][0] = mpatches.Patch(color='blue', label='Price', linestyle='-')
    patches[1][0] = mpatches.Patch(color='green', label='Event', linestyle='-', linewidth=1)
    patches[1][1] = mpatches.Patch(color='red', label='Temperature', linestyle='-', linewidth=1)

    ticks_event = []
    ticks_event.append("No event")
    ticks_event.append("Event occuring")
    ticks_event.append("Large event occuring")
    y = [0, 1, 2]

    ax[0, 0].set(xlabel='Time elapsed (s)', ylabel='Price (euros/kWh)')
    ax[0, 0].legend(handles=[patches[0][0]])
    ax[0, 1].legend()
    ax[0, 1].set_xticks(x, labels)
    ax[1, 0].set(xlabel='Time elapsed (s)', ylabel='Event occuring')
    ax[1, 0].set_yticks(y, ticks_event)
    ax[1, 0].legend(handles=[patches[1][0]])
    ax[1, 1].set(xlabel='Time elapsed (s)', ylabel='Temperature (°C)')
    ax[1, 1].legend(handles=[patches[1][1]])


if __name__ == "__main__":
    if len(sys.argv) != 3:  # Check number of arguments is correct
        print("Usage: python3 main.py {number of homes} {mode}")
        print("The mode can be 0, 1, 2 or 3. See documentation for the description of each mode.")
        sys.exit(0)

    try:  # handling type errors (user doesn't input a number)
        int(sys.argv[1])
        int(sys.argv[2])
    except Exception as e:
        print("Usage: python3 main.py {number of homes} {mode}")
        print("The mode can be 0, 1, 2 or 3. See documentation for the description of each mode.")
        sys.exit(0)

    number_of_homes = int(sys.argv[1])
    homes_type = int(sys.argv[2])

    if (number_of_homes < 0 or homes_type < 0 or homes_type > 3):
        print("Usage: python3 main.py {number of homes} {mode}")
        print("The mode can be 0, 1, 2 or 3. See documentation for the description of each mode.")
        sys.exit(0)

    for i in range(number_of_homes):
        homes_data.append({"id": i, "log": []})

    weather_process = Process(target=weather.create_weather)
    market_process = Process(target=market.market)
    homes_process = Process(target=home_creator.create_homes, args=(number_of_homes, homes_type, ))

    create_connections_thread = threading.Thread(target=create_connections)
    create_connections_thread.start()

    startup_time = time.time()

    print("Starting the weather process...")
    weather_process.start()
    print("Starting the market process...")
    market_process.start()
    print("Creating the homes...")
    homes_process.start()

    time.sleep(2)

    print("Starting the real time plot...")
    ani = animation.FuncAnimation(fig, plotter, interval=250)
    plt.show()

    os.kill(homes_process.pid, signal.SIGALRM)
    os.kill(market_process.pid, signal.SIGALRM)
    os.kill(weather_process.pid, signal.SIGALRM)

    stop_event.set()

    try:
        os.mkdir("output")
    except FileExistsError:
        pass

    with open('output/homes_data.json', 'w') as json_file:
        json.dump(homes_data, json_file,
                indent=4,
                separators=(',', ': '))

    with open('output/market_data.json', 'w') as json_file:
        json.dump(market_data, json_file,
                indent=4,
                separators=(',', ': '))

    with open('output/weather_data.json', 'w') as json_file:
        json.dump(weather_data, json_file,
                indent=4,
                separators=(',', ': '))