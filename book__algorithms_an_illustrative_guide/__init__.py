UNORDERED_ARR = [
    3, 1, 10, 4, 7, 5, 0, -2, 8,
]

ORDERED_LIST = [
    1, 2, 3, 4, 5, 6, 7, 8, 9
]

def recursive_sum(arr):
    if not arr:
        return 0
    return arr.pop(0) + recursive_sum(arr)

def recursive_len(arr):
    if not arr:
        return 0
    arr.pop()
    return 1 + recursive_len(arr)

def recursive_max(arr, maximum=None):
    if not arr:
        return maximum
    current = arr.pop()
    if maximum is None:
        maximum = current
    return recursive_max(arr, maximum=current if current > maximum else maximum)


def binary_search(arr, target):
    low = 0
    height = len(arr) - 1

    while low <= height:
        mid = int((low + height) / 2)
        guess = arr[mid]

        if guess == target:
            return mid
    
        if target > guess:
            low = mid + 1
        else:
            height = mid - 1

    return -1


def binary_search_recursive(arr, target):
    if not arr:
        return -1

    low = 0
    height = len(arr) - 1

    mid = int((low + height) / 2)
    guess = arr[mid]

    print(mid, guess, arr)
    if guess == target:
        return mid
    
    if target > guess:
        return binary_search_recursive(arr[mid + 1:], target)
    return binary_search_recursive(arr[:mid - 1], target)

print(binary_search_recursive(ORDERED_LIST, 3))