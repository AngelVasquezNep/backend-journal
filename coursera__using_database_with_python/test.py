DATA = list(range(0, 99))
LIMIT = 5


def paginated_api(page):
    "Page is index cero based"
    index = page * LIMIT
    return DATA[index: index + LIMIT]




class ApiService:
    def __init__(self):
        self.current_page = 0
        self.results = []

    def fetch(self, n):
        response = []
        while True:
            if len(self.results) >= n:
                response = self.results[0:n]
                self.results = self.results[n:]
                break
            results = paginated_api(self.current_page)
            self.current_page += 1
            self.results += results
            if not results:
                break
        return response


api = ApiService()

print(api.fetch(1)) # [0]
print(api.fetch(1)) # [1]
print(api.fetch(6)) # [2, 3, 4, 5, 6, 7]
print(api.fetch(7)) # [8, 9, 10, 11, 12, 13, 14]
