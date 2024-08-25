import itertools

"""
valid_board = [
    [0, 0, 1, 0],
    [1, 0, 0, 0],
    [0, 0, 0, 1],
    [0, 1, 0, 0],
]

solution = [1, 3, 0, 2] # Index of the queen in each row


Bad solution:
    - Two queens in the same row
    - Two queens in the same column
    - Two queens in the same diagonal

Check if a queen is in the same diagonal:
    - They are in the same diagonal if the difference between their row and column is the same

bad_solution = [
    [0, 0, 1, 1],       # Q1  ->  i = 3, j = 0
    [1, 0, 0, 0],
    [0, 1, 0, 0],       # Q3  ->  i = 1, j = 2
    [0, 0, 0, 0],
]

Diagonal distance between two queens (Q1 and Q3):
    - abs(i1 - i2) == abs(j1 - j2)
    - abs(3 - 1) == abs(0 - 2)
    - 2 == 2

"""


def is_solution(perm: list[int]):
    def is_a_permutation(perm: list[int]):
        return len(set(perm)) == len(perm)

    if not is_a_permutation(perm):
        return False

    for (i1, i2) in itertools.combinations(range(len(perm)), 2):
        # print(f'{i1=}, {i2=}, {perm[i1]=}, {perm[i2]=}')
        if abs(i1 - i2) == abs(perm[i1] - perm[i2]):
            return False

    return True


def can_be_extended_to_solution(perm):
    i = len(perm) - 1
    for j in range(i):
        if i - j == abs(perm[i] - perm[j]):
            return False
    return True


def generate_solutions(board_size, perm=[]):
    solutions = []

    def extend(perm, n):
        if len(perm) == n:
            solutions.append(perm.copy())

        for k in range(n):
            if k not in perm:
                perm.append(k)

                if can_be_extended_to_solution(perm):
                    extend(perm, n)

                perm.pop()
    extend(perm=perm, n=board_size)

    return solutions


print(len(generate_solutions(board_size=8)))


print(is_solution([1, 3, 0, 2]))  # True
# print(is_solution([1, 1, 1, 1])) # False


# for perm in itertools.permutations(range(4)):
#     if is_solution(perm):
#         print(perm)
#         break
