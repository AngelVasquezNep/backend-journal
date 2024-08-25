def transport_a_word(word, transpositions):
    new_word = word.copy()

    def apply(lst, trans):
        first, second = trans
        lst[first], lst[second] = lst[second], lst[first]

    for transposition in transpositions:
        apply(new_word, transposition)

    return new_word


print(
    transport_a_word(
        word=["M", "A", "R", "I", "N", "E"],
        transpositions=[(0, 1), (2, 3), (1, 2), (2, 3), (4, 5)]
    )
)


def transform(first, second):
    assert len(first) == len(second)
    n = len(first)
    assert set(first) == set(range(n))
    assert set(second) == set(range(n))
    transpositions = []
    current = list(first)

    for i in range(n):
        if current[i] != second[i]:
            idx = current.index(second[i])
            print(f'idx = {idx} | current = {current} | second = {second}')
            assert idx != i
            transpositions.append((i, idx))
            current[i], current[idx] = current[idx], current[i]
            assert current[i] == second[i]
    return transpositions


print(transform([3, 4, 0, 2, 1], [1, 0, 3, 4, 2]))
