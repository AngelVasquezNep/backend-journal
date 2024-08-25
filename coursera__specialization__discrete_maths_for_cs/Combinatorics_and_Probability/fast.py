# How many integer numbers from 1 to  1000 are divisible by 2 or by 3?

print(
    len([
        x for x in range(0, 10000) if str(x).count('1') == 0 and str(x).count('3') == 1
    ])
)