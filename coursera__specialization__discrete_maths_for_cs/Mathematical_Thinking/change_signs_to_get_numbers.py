"""
Problem. Is it possible to place signs in the expression
 ± 1 ± 2 ± 3 ± 4 ± 5 ± 6 ± 7 ± 8 ± 9

so that the result is 7, 15, 22, 33, 40, 47?

Max value is 9 + 8 + 7 + 6 + 5 + 4 + 3 + 2 + 1 = 45
Min value is -9 - 8 - 7 - 6 - 5 - 4 - 3 - 2 - 1 = -45

Every odd number between -45 and 45 can be represented by the sum of the numbers from 1 to 9.
"""

def represent(n, value):
    if n == 0 and value == 0:
        return []

    total = sum(range(1, n + 1))

    if abs(value) > total or (total - value) % 2 != 0:
        return False
    
    print(f'n = {n}, value = {value}')

    if value >= 0:
        return represent(n - 1, value - n) + [n]
    else:
        return represent(n - 1, value + n) + [-n]


result = represent(9, 7)
print(f'7 = {result}')


# for v in (7, 15, 22, 33, 40, 47):
#     print(v, end='')
#     result = represent(9, v)
#     if not result:
#         print(' is not representable')
#     else:
#         print('=', end='')
#         for i in result:
#             if i < 0:
#                 print(f'{i}', end='')
#             else:
#                 print(f'+{i}', end='')
#         print()
