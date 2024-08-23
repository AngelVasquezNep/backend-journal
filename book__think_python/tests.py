def any_lowercase(word: str):
    flag = False
    for letter in word:
        flag = flag or letter.islower()
    return flag 

print(any_lowercase('Angelito'))
print(any_lowercase('lito2'))
print(any_lowercase('o3'))
print(any_lowercase('Paps'))