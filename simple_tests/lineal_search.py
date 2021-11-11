def lineal_search(batch, target):
    for element in batch:
        if element == target:
            return True

    return False


if __name__ == "__main__":
    print(lineal_search(range(1, 100), 5))
