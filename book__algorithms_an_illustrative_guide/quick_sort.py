import time

def quick_sort(arr):
    print('----------------')
    print(arr)
    time.sleep(5)
    if len(arr) < 2:
        return arr

    pivot = arr[0]
    grater = []
    less = []

    for item in arr[1:]:
        if item >= pivot:
            grater.append(item)
        else:
            less.append(item)

    print('pivot', pivot)
    print('less', less)
    print('grater', grater)
    
    return quick_sort(less) + [pivot] + quick_sort(grater)

TEST = [
    3, 2, 1, 1, 3, 10, 35, -1, 15, 3, 4,
]

print(quick_sort(TEST))