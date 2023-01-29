# PPC Project

The goal of this programming project is to design and implement a multi-process and multi-thread simulation in Python. The program simulates an energy market where energy-producing and consuming homes, weather conditions and random events contribute to the evolution of energy price over time.

## Features

The program simulates a desired number of energy-consuming and producing homes. They interact with a market, which calculates the current price of the energy based on different factors:
 - The current temperature (dynamically updated by a script)
 - Whether an "event" is occuring, which could be a new law or a fuel shortage (dynamically updated as well)

The homes consume a variable amount of energy, depending on the temperature. They always produce the same amount of energy. When they run out of energy, they can buy some from the market at the current price, try to take some from the community or ask for the community for energy.

The homes can have different strategy regarding the energy they produce:
 - Always give: when producing too much energy, the home will give it to the community. Other homes in lack of energy can then take energy from the community freely.
 - Always sell: when producing too much energy, the home will sell it to the market, thus earning money.
 - Sell if no askers: when producing too much energy, the home will sell it to the market, only if no other homes are asking for energy.

The program displays graphs representing the evolution of the simulation (the price, the temperature, the events, and the balance and energy of each home) in real time.

## Usage

First install the required packages:

```pip install -r requirements.txt```

Then run the program:

```python3 main.py {number of homes} {mode}```

The number of homes you want in the simulation is {number of homes}

The parameter {mode} can be one of the following:
 - 0: each home will pick a random strategy out of the three possible
 - 1: all homes will follow the "always give" strategy 
 - 2: all homes will follow the "always sell" strategy 
 - 3: all homes will follow the "sell if no askers" strategy 

## Team

<a href="https://github.com/vqlion"><img src="https://avatars.githubusercontent.com/u/104720049?v=4" width="75"></a> 

[Valentin Jossic](https://vqlion.me)