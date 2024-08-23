"""
 /$$$$$$$$                                         /$$                              
| $$_____/                                        |__/                              
| $$       /$$   /$$  /$$$$$$   /$$$$$$   /$$$$$$$ /$$  /$$$$$$$  /$$$$$$   /$$$$$$$
| $$$$$   |  $$ /$$/ /$$__  $$ /$$__  $$ /$$_____/| $$ /$$_____/ /$$__  $$ /$$_____/
| $$__/    \  $$$$/ | $$$$$$$$| $$  \__/| $$      | $$|  $$$$$$ | $$$$$$$$|  $$$$$$ 
| $$        >$$  $$ | $$_____/| $$      | $$      | $$ \____  $$| $$_____/ \____  $$
| $$$$$$$$ /$$/\  $$|  $$$$$$$| $$      |  $$$$$$$| $$ /$$$$$$$/|  $$$$$$$ /$$$$$$$/
|________/|__/  \__/ \_______/|__/       \_______/|__/|_______/  \_______/|_______/ 
"""

"""
Write a script that reads the current time and converts it to a time of day in
hours, minutes, and seconds, plus the number of days since the epoch.
"""


import time
MINUTE_IN_SECONDS = 60
HOUR_IN_SECONDS = MINUTE_IN_SECONDS * 60
DAY_IN_SECONDS = HOUR_IN_SECONDS * 24
YEAR_IN_SECONDS = DAY_IN_SECONDS * 365


def parsed_time():
    reminder = time.time()

    years = reminder // YEAR_IN_SECONDS
    reminder = reminder % YEAR_IN_SECONDS

    days = reminder // DAY_IN_SECONDS
    reminder = reminder % DAY_IN_SECONDS

    hours = reminder // HOUR_IN_SECONDS
    reminder = reminder % HOUR_IN_SECONDS

    minutes = reminder // MINUTE_IN_SECONDS
    reminder = reminder % MINUTE_IN_SECONDS

    seconds = reminder

    print(f"{years=} | {days=} | {hours=} | {minutes=} | {seconds=}")


"""
Fermat's Last Theorem says that there are no positive integers a, b, and c such that 
    a^n + b^n = c^n
for any values of n grater than 2.

    1. Writte a function named check_fermat that takes four parameters
        -- a, b, c and n -- and checks to see if Fermat's theorem holds.
        If n is greater than 2 and 
            a^n + b^n = c^n
        the program should print, "Holy smokes, Fermat was wrong!"
        Otherwise the program should print, "No, that doesn't work."
    2. Write a function that prompts the user input values for a, b, c
        and n, converts them to integers, and uses check_fermat to check
        whether they violate Fermat's theorem.
"""


def check_fermat(a, b, c, /, n):
    if n <= 2:
        print("n should be gratter than 2.")
    if a**n + b**n == c**2:
        print("Holy smokes, Fermat was wrong!")
    else:
        print("No, that doesn't work.")


def user_check_fermat():
    print("Fermat's theorem shape: a^n + b^n = c^n with n>2 and a,b,c positive numbers.")
    print("Give your values for a, b, c and n:")
    a = int(input("a: "))
    b = int(input("b: "))
    c = int(input("c: "))
    n = int(input("n: "))
    check_fermat(a, b, c, n=n)


if __name__ == "__main__":
    option = int(input("""
    Choise an option:
        1) parsed_time: Time from EPOCH.
        2) check_fermat: Try Fermat's Theorem your self
    Your option: 
    """))

    if option == 1:
        parsed_time()
    elif option == 2:
        user_check_fermat()
    else:
        print("Select a valid (numeric) option.")