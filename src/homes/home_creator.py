import sys
import home
from multiprocessing import Queue

INIT_BALANCE = 100
INIT_ENERGY = 10

if __name__ == "__main__":
    number_of_homes = 0

    try:
        number_of_homes = int(sys.argv[1])
    except Exception:
        sys.exit(1)

    number_of_homes = int(sys.argv[1])
    process_list = []

    for _ in range(number_of_homes):
        give_queue = Queue()
        ask_queue = Queue()
        home_process = home.Home(INIT_BALANCE, INIT_ENERGY, give_queue, ask_queue, 1)
        home_process.start()
        process_list.append(home_process)

    for process in process_list:
        process.join()