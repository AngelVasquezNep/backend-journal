"""
You're a farmer and you're trying to find the greatest square box size to divide
your land in same squares.
"""

def gratest_square(width, height):
    largest_size = width
    smallest_size = height
    if height > width:
        largest_size = height
        smallest_size = width

    remaining = largest_size % smallest_size
    if remaining == 0:
        return smallest_size

    return gratest_square(width=largest_size, height=remaining)


print(gratest_square(width=1680, height=640))