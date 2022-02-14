# Pandas

Pandas is a package to handle with hight order data.
It's built from NumPy.

It works better with DataFrame info (tabular info): It's like SQL or Excel info.


## Usage
```python
import pandas as pd

students_dict = {
    "name": ["Miguel", "Juan David", "Carmen", "Facundo", "Romina"],
    "age": [29, 19, 24, 22, 25],
    "career path":  ["Data Analyst", "Data Scientist", "Data Analyst", "Data Engineer", "ML Engineer" ],
}

students_df = pd.DataFrame(students_dict)
# >>> print(students_df)
#          name  age     career path
# 0      Miguel   29    Data Analyst
# 1  Juan David   19  Data Scientist
# 2      Carmen   24    Data Analyst
# 3     Facundo   22   Data Engineer
# 4      Romina   25     ML Engineer

students_list = [
    {"name": "Miguel", "age": 29, "career path": "Data Analyst"},
    {"name": "Juan David", "age": 19, "career path": "Data Scientist"},
    {"name": "Carmen", "age": 24, "career path": "Data Analyst"},
]

students_df_2 = pd.DataFrame(students_list)
# >>> print(students_df)
#          name  age     career path
# 0      Miguel   29    Data Analyst
# 1  Juan David   19  Data Scientist
# 2      Carmen   24    Data Analyst
# 3     Facundo   22   Data Engineer
# 4      Romina   25     ML Engineer


# >>> print(students_df_2.dtypes)
# name           object
# age             int64
# career path    object
# dtype: object
```

## Import Data

```python
# pd.read_{file_type}('path')

import pandas as pd

df = pd.read_csv('pandas_notes/studentsperformance.csv')
print(df)

#      gender  ... writing score
# 0    female  ...            74
# 1    female  ...            88
# 2    female  ...            93
# 3      male  ...            44
# 4      male  ...            75
# ..      ...  ...           ...
# 995  female  ...            95
# 996    male  ...            55
# 997  female  ...            65
# 998  female  ...            77
# 999  female  ...            86

# [1000 rows x 8 columns]
```

## Free Datasets

[kaggle](https://www.kaggle.com/datasets)

## Useful Info

```python

df.info()

# RangeIndex: 65 entries, 0 to 64
# Data columns (total 8 columns):
#  #   Column                         Non-Null Count  Dtype  
# ---  ------                         --------------  -----  
#  0   Country_code                   65 non-null     object 
#  1   Country                        65 non-null     object 
#  2   Total Library Size             65 non-null     int64  
#  3   No. of TV Shows                65 non-null     int64  
#  4   No. of Movies                  65 non-null     int64  
#  5   Cost Per Month - Basic ($)     65 non-null     float64
#  6   Cost Per Month - Standard ($)  65 non-null     float64
#  7   Cost Per Month - Premium ($)   65 non-null     float64
# dtypes: float64(3), int64(3), object(2)
# memory usage: 4.2+ KB


df.describe()


#        Total Library Size  ...  Cost Per Month - Premium ($)
# count           65.000000  ...                     65.000000
# mean          5314.415385  ...                     15.612923
# std            980.322633  ...                      4.040672
# min           2274.000000  ...                      4.020000
# 25%           4948.000000  ...                     13.540000
# 50%           5195.000000  ...                     14.450000
# 75%           5952.000000  ...                     18.060000
# max           7325.000000  ...                     26.960000


df.columns
# Index([
#           'Country_code',
#           'Country',
#           'Total Library Size',
#           'No. of TV Shows',
#           'No. of Movies',
#           'Cost Per Month - Basic ($)',
#           'Cost Per Month - Standard ($)',
#           'Cost Per Month - Premium ($)'
#       ],
#       dtype='object',
# )


# Access one column

df['No. of TV Shows']
# 0     3154
# 1     4050
# 2     3779
# 3     3374
# 4     3155
#       ... 
# 60    3261
# 61    4551
# 62    3826
# 63    3154
# 64    3154
# Name: No. of TV Shows, Length: 65, dtype: int64

df['No. of TV Shows'].mean()
# 3518.9538461538464

df['No. of TV Shows'].median()
# 3512.0

df['No. of TV Shows'].std()
# 723.0105555671636
```