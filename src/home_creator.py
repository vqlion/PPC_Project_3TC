from src.constants import *
from src import home
from multiprocessing import Queue
import sysv_ipc
import signal
import os

process_list = []

def handler_alrm(sig, frame):
    global process_list
    if sig == signal.SIGALRM:
        for process in process_list:
            print("home creator receveived signal to terminate")
            os.kill(process.pid, signal.SIGALRM)


def create_homes(number_of_homes):
    global process_list
    signal.signal(signal.SIGALRM, handler_alrm)

    mq = sysv_ipc.MessageQueue(MESSAGE_QUEUE_KEY, sysv_ipc.IPC_CREAT)
    for i in range(number_of_homes):
        home_process = home.Home(INIT_BALANCE, INIT_ENERGY, 1, i)
        home_process.start()
        process_list.append(home_process)

    for process in process_list:
        process.join()
    mq.remove()