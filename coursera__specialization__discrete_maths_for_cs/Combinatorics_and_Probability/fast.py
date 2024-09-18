"""
How many integer numbers from 1 to  1000 are divisible by 2 or by 3?
"""

print(
    len([
        x for x in range(0, 10000) if str(x).count('1') == 0 and str(x).count('3') == 1
    ])
)

"""
You have 5 friends, but there are only 3 vacant places in your car.
How many ways are there to make the journay?

R: There are 5 choices for the first friend, 4 for the second and 3 for the third
friend.

5 x 4 x 3 / 3! = 10
"""

from itertools import combinations


for c in combinations(["Vero", "Neto", "Isra", "Andy", "David"], 3):
    print(c)

