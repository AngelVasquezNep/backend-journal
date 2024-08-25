"""
Chapter 9
Case study: Word play

It uses CROSSW.TXT file
"""
import string
from typing import Tuple, Union


def is_bigger_than(word: str, size: int) -> bool:
    return len(word.replace(" ", "")) > size


def has_letter(target: str, word :str) -> bool:
    return target in word


def has_no_e(word:str) -> bool:
    return not has_letter('e', word)


def avoids(word: str, forbidden: str) -> bool:
    """
    Check if a words doesn't contain any forbidden letter
    Args:
        word str
        forbidden (str): A sequence of letters without space
    """
    for f in forbidden:
        if has_letter(f, word):
            return False
    return True


def order_characters_by_usage(words: list[str]) -> list[Tuple[str, float]]:
    """
    Given a list (words) returns Alphabet list ordered by % usage, it means
    how many words are using 'a', how many are using 'b', etc
    Example:
        >>> order_characters_by_usage(['wather', 'tree'], 'a')
        >>> [('a', 50)]
        >>> order_characters_by_usage(['wather', 'tree'], 'b')
        >>> [('b', 0)]
    """

    results = []
    for letter in string.ascii_lowercase:
        result = len([word for word in words if has_letter(letter, word)])
        percentage = result * 100 / len(words)
        results.append((letter, percentage))
    return sorted(results, key=lambda result: result[1])


def uses_all(word: str, required: str) -> bool:
    for letter in required:
        if not has_letter(letter, word):
            return False
    return True


def is_abecedarian(word):
    return word == "".join(sorted(word))


def consecutive_double_letters(word: str, coincidences: int) -> bool:
    assert coincidences > 0, "Coincidences must be greatter than cero"
    try:
        index = 0
        founded = 0
        while founded < coincidences:
            prev_char = word[index]
            next_char = word[index + 1]
            if prev_char == next_char:
                founded += 1
                index += 1
            index+=1
        return founded == coincidences
    except IndexError:
        return False



def reversive_age(age: int) -> list[int]:
    """
    Try to find how many times the given mon's age was reversible with her child
    Example:
        mom's age 73
        child age 37

        That's one reverse coincidence, how many times that mon and her child
        haved a reversible age?
    """
    assert 0 < age < 100, "Age out of range, try with values from 1 to 99"

    def str_format(value: Union[int, str]) -> str:
        return str(value).zfill(2)

    def to_reverse(value: Union[int, str]) -> str:
        return "".join(reversed(str_format(value)))

    age = str_format(age)
    child = to_reverse(age)
    diff = abs(int(age) - int(child))

    coincidences = []

    for age in range(0, 99):
        mom_age = str_format(age + diff)
        if str_format(age) == to_reverse(mom_age):
            coincidences.append((age, mom_age))

    return coincidences


if __name__ == "__main__":
    print(reversive_age(73))
    print(reversive_age(37))
    print("bookkeeper", consecutive_double_letters("bookkeeper", 0))
    raise Exception('Stop') 
    
    words = []
 
    with open('CROSSWD.TXT', 'r') as f:
        words = [word.strip() for word in f]

    """
    Exercise 1
    Write a program that reads 'words.txt' and prints only the words with more
    than 20 characters (not counting whitespaces)
    """

    response = [word for word in words if is_bigger_than(word, 20)]
    print("More than 20 characters", response)

    """
    Exercise 2
    Write a function calle has_no_e that returns True if the given word doesn't
    have the letter "e" in it.

    Print only the words that have no "e" and compute the percentage of
    the words in the list that have no "e".
    """

    with_no_e = [word for word in words if has_no_e(word)]
    print("With no e (just last 5 words)", with_no_e[-5:])
    print("% without e", len(with_no_e) * 100 / len(words), "%")


    """
    Exercise 3
    Write a function named 'avoids' that takes a word and a string of forbidden
    letters, and that returns True if the word doesn't use any of the forbidden
    letters.

    Modify your program to prompt the user to enter a string forbidden letters
    and then print the number of words that don't contain any of them.

    Can you find a combination of five forbidden letters that excludes the
    smallest number of words?
    """

    user_prompts = [
        'aeio',
        'u',
        'e',
        'aeiou',
    ]

    for forbidden in user_prompts:
        result = [word for word in words if avoids(word, forbidden)]
        print(f"{len(result)} words don't contain any of '{forbidden}' words")

    
    for letter in string.ascii_lowercase:
        result = len([word for word in words if has_letter(letter, word)])
        percentage = result * 100 / len(words)
        print(f"Letter '{letter}' is {percentage}%")


    less_used_words = order_characters_by_usage(words)[0:5]
    print("Less used words", less_used_words)

