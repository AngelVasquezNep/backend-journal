def bubble_sort(elements):
    n = len(elements)
    steps = 0

    for i in range(n):
        for j in range(0, n - i - 1):
            steps += 1
            if elements[j] > elements[j + 1]:
                aux = elements[j]
                elements[j] = elements[j + 1]
                elements[j + 1] = aux
    return (elements, steps)


if __name__ == "__main__":
    elements = [3, 5, 7, 1, 6, 8, 10, 2, 9, 4]
    sorted_elements, steps = bubble_sort(elements)
    print(sorted_elements, steps)
