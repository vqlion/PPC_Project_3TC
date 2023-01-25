import threading
from multiprocessing.managers import SyncManager
import random
import time
import sys

sys.path.append('../')
from constants import *


class DictManager(SyncManager): pass

weather_updates = {}
def get_dict():
    return weather_updates

def weather_server():
    DictManager.register('weather_updates', get_dict)
    m = DictManager(address=('', SHARED_MEMORY_PORT), authkey=SHARED_MEMORY_KEY)
    s = m.get_server()
    s.serve_forever()

if __name__ == "__main__":
    server = threading.Thread(target=weather_server)
    server.start()
    weather_updates.update(([('temp', 15)]))

    while True:
        timeout = random.randint(1,15)
        temp = weather_updates.get('temp')
        new_temp = temp + random.randint(-1, 1) 
        time.sleep(timeout)
        weather_updates.update(([('temp', new_temp)]))
        print(weather_updates)
