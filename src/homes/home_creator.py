import sys
import home

INIT_BALANCE = 1000
INIT_ENERGY = 100

if __name__ == "__main__":
    number_of_homes = 0

    try:
        number_of_homes = int(sys.argv[1])
    except Exception:
        sys.exit(1)

    number_of_homes = int(sys.argv[1])

    for _ in range(number_of_homes):
        home_process = home.Home(INIT_BALANCE, INIT_ENERGY)
        home_process.start()