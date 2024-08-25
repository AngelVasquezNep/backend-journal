def binary_search(items, target):
    low = 0
    hight = len(items) - 1

    while low <= hight:
        mid = int((low + hight) / 2)
        guess = items[mid]

        if guess == target:
            return mid

        if guess > target:
            hight = mid - 1
        else:
            low = mid + 1

    return None


print(binary_search([1, 2, 3, 4, 5], 5))