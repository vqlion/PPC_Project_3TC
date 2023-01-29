from src.constants import *
from src import home
from multiprocessing import Queue
import sysv_ipc
import signal
import os
import random

process_list = []

def handler_alrm(sig, frame):
    global process_list
    if sig == signal.SIGALRM:
        for process in process_list:
            os.kill(process.pid, signal.SIGALRM)


def create_homes(number_of_homes, homes_type):
    global process_list
    signal.signal(signal.SIGALRM, handler_alrm)

    mq = sysv_ipc.MessageQueue(MESSAGE_QUEUE_KEY, sysv_ipc.IPC_CREAT)
    for i in range(number_of_homes):
        strategy = homes_type if homes_type != 0 else random.randint(1, 3)
        home_process = home.Home(INIT_BALANCE, INIT_ENERGY, strategy, i)
        home_process.start()
        process_list.append(home_process)

    for process in process_list:
        process.join()
    mq.remove()