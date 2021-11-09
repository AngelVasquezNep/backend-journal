import time


class Fibo:
    def __init__(self, max=None):
        if max is not None:
            assert max > 0, "max should be greatter than 0"
        self.max = max

    def __iter__(self):
        self.n1 = 0
        self.n2 = 1
        self.counter = 0
        return self

    def __next__(self):
        if self.max is not None and self.counter == self.max:
            raise StopIteration

        if self.counter == 0:
            self.counter += 1
            return self.n1
        if self.counter == 1:
            self.counter += 1
            return self.n2

        result = self.n1 + self.n2
        self.n1 = self.n2
        self.n2 = result

        self.counter += 1

        return result


if __name__ == "__main__":
    for num in Fibo(5):
        print(num)
        time.sleep(1)
