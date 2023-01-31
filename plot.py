import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import json

#again a lot of complicated lines to have beautiful graphs
#not very interesting, and the docs describe it better than me (https://matplotlib.org/3.6.3/api/index.html)

homes_data = json.load(open("output/homes_data.json"))
market_data = json.load(open("output/market_data.json"))
weather_data = json.load(open("output/weather_data.json"))

fig, ax = plt.subplots(3, 1, num="Summary")

ax[0].plot([d["time"] for d in market_data], [d["price"] for d in market_data], 'b')
ax[2].plot([d["time"] for d in weather_data], [d["temp"] for d in weather_data], 'r')
ax[1].plot([d["time"] for d in weather_data], [d["rain"]for d in weather_data], 'b--')
ax[1].plot([d["time"] for d in market_data], [d["event"] for d in market_data], 'g')

patches = [None for _ in range(3)]

patches[0] = mpatches.Patch(color='blue', label='Price', linestyle='-')
event_patch = [mpatches.Patch(
        color='green', label='Event', linestyle='-', linewidth=0.1), mpatches.Patch(
        color='blue', label='Rain', linestyle='-', linewidth=0.1)]
patches[2] = mpatches.Patch(color='red', label='Temperature', linestyle='-', linewidth=1)

ticks_event = ["No event", "Event occuring", "Large event occuring"]
y = [0, 1, 2]

ax[0].set(xlabel='Time elapsed (s)', ylabel='Price (euros/kWh)')
ax[0].legend(handles=[patches[0]])
ax[1].set(xlabel='Time elapsed (s)', ylabel='Event occuring')
ax[1].set_yticks(y, ticks_event)
ax[1].legend(handles=event_patch)
ax[2].set(xlabel='Time elapsed (s)', ylabel='Temperature (°C)')
ax[2].legend(handles=[patches[2]])

for home in homes_data:
    plt.figure(f'Home {home["id"] + 1}')
    plt.plot([d["time"] for d in home["log"]], [d["balance"] for d in home["log"]], 'b', label="Balance")
    plt.plot([d["time"] for d in home["log"]], [d["energy"] for d in home["log"]], 'r', label="Energy")
    plt.legend()
    plt.xlabel("Time elapsed since the beginning (s)")
    plt.ylabel("Energy (euros) and balance (kWh) held by the home")
    plt.title(f'Home {home["id"] + 1}')


plt.show()