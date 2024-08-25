import operator

RESPONSES = {
    "L": "LARGER",
    "S": "SMALLER",
}


def guess_the_number(limit: int):
    last_guess = limit
    current_guess = int(limit / 2)

    while True:
        try:
            response = input(f'Is it {current_guess} ? \n').upper()
        except:
            break
        aux = current_guess
        difference = (abs(current_guess - last_guess) / 2)
        USER_ACTION = RESPONSES.get(response)

        operation = operator.add if USER_ACTION == "LARGER" else operator.sub
        current_guess = int(operation(current_guess, difference))
        last_guess = aux


if __name__ == "__main__":
    guess_the_number(2_097_152)
