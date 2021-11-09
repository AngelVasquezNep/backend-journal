import time


def fibo_gen(max=None):
    n1 = 0
    n2 = 1
    counter = 0

    counter += 1
    yield n1

    counter += 1
    yield n2

    while max is None or max > counter:
        result = n1 + n2
        n1 = n2
        n2 = result

        counter += 1

        yield result


if __name__ == "__main__":
    fibo = fibo_gen(max=5)

    for n in fibo:
        print(n)
        time.sleep(1)
