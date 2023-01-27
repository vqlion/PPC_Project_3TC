import sys
sys.path.append('../')
from constants import *
import home
from multiprocessing import Queue
import sysv_ipc

INIT_BALANCE = 10
INIT_ENERGY = 2

if __name__ == "__main__":
    number_of_homes = 0

    try:
        number_of_homes = int(sys.argv[1])
    except Exception:
        sys.exit(1)

    number_of_homes = int(sys.argv[1])
    process_list = []

    mq = sysv_ipc.MessageQueue(MESSAGE_QUEUE_KEY, sysv_ipc.IPC_CREAT)
    for i in range(number_of_homes):
        home_process = home.Home(INIT_BALANCE, INIT_ENERGY, 1, i)
        home_process.start()
        process_list.append(home_process)

    for process in process_list:
        process.join()
    mq.remove()