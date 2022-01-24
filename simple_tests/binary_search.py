"""
Binary search:
  It assumes that target list is sorted
"""

import random


def binary_recursive_search(elements, start, end, target, count = 0):
    if start > end:
        return (False, count)

    count+=1
    middle = (start + end) // 2

    if elements[middle] == target:
        return (True, count)
    if elements[middle] < target:
        return binary_recursive_search(elements, middle + 1, end, target, count)
    if elements[middle] > target:
        return binary_recursive_search(elements, start, middle - 1, target, count)


def binary_search(elements, target):
    """
    Args:
        elements (list)
        target (Any)
    Returns:
        Index of
    """
    left, rigth = 0, len(elements) - 1

    while left <= rigth:
        print(f'Searching {target} between {elements[left]} and {elements[rigth]}')
        middle = (left + rigth) // 2

        if elements[middle] == target:
            return middle
        elif elements[middle] < target:
            left = middle + 1
        elif elements[middle] > target:
            rigth = middle - 1
    return -1

LIMIT = 1_000
random_list = list(sorted([random.randint(0, 100) for i in range(0, LIMIT)]))

if __name__ == "__main__":
    bs = binary_search(random_list, 20)
    print(bs)