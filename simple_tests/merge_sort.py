
def merge_sort(elements, steps=0):
    if len(elements) > 1:
        middle = len(elements) // 2
        left = elements[:middle]
        right = elements[middle:]

        # Recursive call on each half
        l, _steps_left = merge_sort(left, steps)
        l, _steps_right = merge_sort(right, steps)
        steps += _steps_left
        steps += _steps_right

        # Two iterators for traversing the two halves
        i = 0
        j = 0

        # Iterator for the main list
        k = 0

        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                # The value from the left half has been used
                elements[k] = left[i]
                # Move the iterator forward
                i += 1
            else:
                elements[k] = right[j]
                j += 1
            # Move to the next slot
            k += 1

        # For all the remaining values
        while i < len(left):
            elements[k] = left[i]
            i += 1
            k += 1

        while j < len(right):
            elements[k] = right[j]
            j += 1
            k += 1
        steps += k

    return (elements, steps)


if __name__ == "__main__":
    unordered_list = [38, 27, 43, 3, 9, 82, 10]
    ordered_list, steps = merge_sort(unordered_list)
    print(ordered_list, steps)
