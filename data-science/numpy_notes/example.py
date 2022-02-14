import numpy as np


def run():
    vector = np.array([1, 2, 4, 8, 16])
    print(vector)
    print(vector.shape)
    print(vector.dtype)

    matrix = np.array([[5, 10, 11], [15, 30, 12]])
    print(matrix)
    print(matrix.shape)
    print(matrix.dtype)

    matrix_2 = np.array([[5, 10, 11], [15, 30, 12], [15, 30, 12]])
    print(matrix_2)
    print(matrix_2.shape)
    print(matrix_2.dtype)
    


if __name__ == "__main__":
    run()
