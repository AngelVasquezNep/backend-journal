# NumPy

It's used to handle matrixs and hight math functions.
It can handle complex files like:
- Images
- Video
- Sound
- Etc.

## Arrays (Ranks)

- Rank 0 - Exacalar: (I think it's) A simple value
- Rank 1 - Unidimensional (Vector): A simple list
- Rank 2 - Bidimensiona (Matrix): Like a table
- Rank 3 - Three dimensions or more (Tensor): Matrix of Matrixs.

## Usage

```python
import numpy as np

# Create an array
# my_array = np.array(my_list)

vector = np.array([1, 2, 4, 8, 16])
print(vector)
# >>> [ 1  2  4  8 16]

matrix = np.array(
  [
    [5, 10, 11],
    [15, 30, 12]
  ])
print(matrix)
# >>> [[ 5 10 11]
#  [15 30 12]]
```

## Dimensions

1. One dimension (Vector): Count elements
```python
vector.shape
>>> (5,)
```
2. Two dimensions (Matrix): Row, Columns
```python
matrix.shape
>>> (2, 2)
```

2. Three dimensions or more (Tensor): Deep, Row, Columns
```python
tensor.shape
>>> (4, 2, 3)
```

## Data type

```python
print(vector.dtype)
>>> "int64"
print(float_vector.dtype)
>>> "float64"
```

## Tutorials

[Numpy Platzi (quick)Tutorial](https://platzi.com/blog/numpy/)

[Anthony manotoa python tutorials](https://platzi.com/blog/autores/anthony_manotoa/)
