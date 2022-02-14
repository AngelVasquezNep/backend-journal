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

print('*' * 50)

students_list = [
    {"name": "Miguel", "age": 29, "career path": "Data Analyst"},
    {"name": "Juan David", "age": 19, "career path": "Data Scientist"},
    {"name": "Carmen", "age": 24, "career path": "Data Analyst"},
]

students_df_2 = pd.DataFrame(students_list)
print(students_df_2)
print(students_df_2.dtypes)