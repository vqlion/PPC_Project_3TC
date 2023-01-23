from multiprocessing import Process
import os
import signal
import random
import time

class ExternalEvent(Process):
    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            timeout = random.randint(1,60)
            time.sleep(timeout)
            os.kill(os.getppid(), signal.SIGUSR1)