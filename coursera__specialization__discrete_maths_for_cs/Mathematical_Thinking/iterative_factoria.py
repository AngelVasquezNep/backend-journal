def recursive_factorial(n):
    assert(n > 0)
    if n == 1:
        return 1

    return n * recursive_factorial(n=n - 1)


def iterative_factoria(n):
    assert(n > 0)
    result = 1

    for i in range(1, n + 1):
      result *= i

    return result

print(recursive_factorial(n=5))
print(iterative_factoria(n=5))
