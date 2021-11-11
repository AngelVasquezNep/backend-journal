"""
To work with temporal algorithm complexity 
"""
from execution_time import execution_time

@execution_time
def factorial(n):
    result = 1

    while n > 1:
        result *= n
        n -= 1

    return result


@execution_time
def recursive_factorial(n):
    if n == 1:
        return 1

    return n * recursive_factorial(n - 1)


if __name__ == "__main__":
    factorial(1_000_000_000)