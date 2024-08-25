"""
board = [
  [ / , / , / ,   , \ ],
  [   ,   , / ,   , \ ],
  [ \ , \ ,   , \ , \ ],
  [ \ ,   , / ,   ,   ],
  [ \ ,   , / , / , / ],
]
"""

def can_be_extended_to_solution(perm):
    i = len(perm) - 1
    for j in range(i):
        if i - j == abs(perm[i] - perm[j]):
            return False
    return True

def generate_solutions(perm, n):
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
    extend(perm = perm, n = n)

    return solutions

print(len(generate_solutions(perm = [], n = 8)))