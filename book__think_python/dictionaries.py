def histogram(word: str) -> dict:
    result = {}
    for letter in word:
        if not result.get(letter):
            result[letter] = 0
        result[letter] += 1
    return result


def invert_dict(d: dict) -> dict:
    result = {}
    for key in d:
        value = d.get(key)
        if not result.get(value):
            result[value] = []
        result[value].append(key)
    return result



know_fibonacci_results = { 0:0, 1:1 }

def fibonacci(n):
    if n in know_fibonacci_results:
        return know_fibonacci_results[n]
    res = fibonacci(n-1) + fibonacci(n-2)
    know_fibonacci_results[n] = res
    return res


if __name__ == "__main__":
    from pprint import pprint as pp
    pp(histogram('palindromee'))
    pp(invert_dict(histogram('palindromee')))
    print(fibonacci(100))
