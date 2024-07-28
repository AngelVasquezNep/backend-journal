def first(word):
    return word[0]


def last(word):
    return word[-1]


def middle(word):
    return word[1:-1]


def palindrome(word):
    size = len(word)

    if size == 0 or size == 1:
        return True

    return first(word) == last(word) and palindrome(middle(word))


print('None', palindrome(''))
print('a', palindrome('a'))
print('ab', palindrome('ab'))
print('aa', palindrome('aa'))
print('abc', palindrome('abc'))
print('aba', palindrome('aba'))
print('acca', palindrome('acca'))
print('aczca', palindrome('aczca'))
print('acññca', palindrome('acññca'))

