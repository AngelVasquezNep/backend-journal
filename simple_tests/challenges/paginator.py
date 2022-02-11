import math

DATA = [i for i in range(0, 100)]
PAGE_SIZE = 5


def api_call(page):
    print("API_CALL", page)
    index = page * PAGE_SIZE
    return DATA[index:index + PAGE_SIZE]


class ApiConsumer:
    def __init__(self, page_size=PAGE_SIZE, api_call=api_call) -> None:
        self.index = 0
        self.page = -1
        self.store = []
        self.page_size = page_size
        self.api_call = api_call

    def fetch(self, retreive_count):
        self.index += retreive_count
        next_page = math.floor(self.index / self.page_size)

        if next_page > self.page:
            self.page = next_page
            self.store += self.api_call(page=next_page)

        response = self.store[:retreive_count]
        self.store = self.store[retreive_count:]
        return response


# Current usage
# print(api_call(0))  # >>> [0, 1, 2, 3, 4]
# print(api_call(100))  # >>> []
# print(api_call(17))  # >>> [85, 86, 87, 88, 89]


consumer = ApiConsumer()

# assert(consumer.fetch(2) == [0, 1])
# assert(consumer.fetch(4) == [2, 3, 4, 5])
# assert(consumer.fetch(1) == [6])

print(consumer.fetch(2))
print(consumer.fetch(4))
print(consumer.fetch(1))
