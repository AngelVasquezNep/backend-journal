def generate_permutations(n, perm = []):
    if len(perm) == n:
        print(perm)
        return perm

    for k in range(n):
        if k not in perm:
            perm.append(k)
            generate_permutations(n, perm)
            perm.pop()


generate_permutations(3)