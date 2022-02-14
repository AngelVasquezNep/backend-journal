import pandas as pd

df = pd.read_csv('pandas_notes/netflix_subscription_fee.csv')


def logger(result, divisor="\n"):
    print(result)
    print(divisor)


logger(df)
logger(df.info())
logger(df.describe())

# -------------------

logger(df.columns)

logger(df['No. of TV Shows'])
logger(df['No. of TV Shows'].mean())
logger(df['No. of TV Shows'].median())
logger(df['No. of TV Shows'].std())