"""
Original list:          Sorted list:
    - 10                    - Empty
    - 3
    - 5

After found the samllest index (1):
Original list:          Sorted list:
    - 10                    -3
    - 5
"""

def find_smallest(arr:list) -> list:
    smallest = arr[0]
    smallest_index = 0

    for i in range(1, len(arr)):
        if arr[i] < smallest:
            smallest = arr[i]
            smallest_index = i
    return smallest_index

arr = [10, 2, 3, 4, 5]

def selection_sort(arr):
    new_arr = []
    for i in range(len(arr)):
        smallest_index = find_smallest(arr)
        new_arr.append(arr.pop(smallest_index))
    return new_arr

print(arr)
print(selection_sort(arr))
print(arr)