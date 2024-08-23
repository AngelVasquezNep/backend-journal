def right_justify(word):
    size = len(word)
    offset = 70 - size
    spam = " " * offset
    print(spam + word)

right_justify("month")


def do_twice(fn, arg):
    fn(arg)
    fn(arg)

do_twice(right_justify, "month")


def do_n(fn, n, /, *arg):
    for i in range(n):
        fn(*arg)

def print_square(size):

    def print_line(edge, separator, size):
        separator = separator + " "
        corner = edge + (separator * size)
        line = corner + corner + edge
        print(line)

    print_line("+", "-", size)
    do_n(print_line, size, "|", " ", size)
    print_line("+", "-", size)
    do_n(print_line, size, "|", " ", size)
    print_line("+", "-", size)


print_square(5)
