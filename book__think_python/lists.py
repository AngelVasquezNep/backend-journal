def sum_nested_lists(arr_numbers: list[list[int]]) -> int:
    return sum([sum(numbers) for numbers in arr_numbers])


def is_sorted(arr: list[int]) -> bool:
    if len(arr) < 2:
        return True

    index = 0
    while index < len(arr) - 1:
        index += 1
        if arr[index - 1] > arr[index]:
            return False
    return False


if __name__ == "__main__":
    print(sum_nested_lists([ [1, 2], [3, 4], [4, 6] ]))

    print(is_sorted([1, 2, 3, 4]))
