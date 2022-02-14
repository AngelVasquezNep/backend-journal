import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


#
# Gráficas de líneas
#

# x = [2015, 2016, 2017, 2018, 2019, 2020, 2021]
# y = [   1,    2,    5,   10,   21,   40,   54]

# plt.plot(x, y, marker='o', linestyle=':', color='g')
# plt.xlabel('Years')
# plt.ylabel('Revenue')
# plt.title('Revenue per year')
# plt.show()




#
# Gráfica de barras - Bar plot
#

# x = ['Data Science', 'Web Development', 'Mobile Development']
# y = [400, 500, 250]

# plt.bar(x, y)
# plt.show()




#
# Histograma
#

# prices = [1000, 2300, 3001, 3450, 4200, 4780, 5100, 5500, 6000, 7500, 7900]
# bins = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]

# plt.hist(prices, bins)
# plt.show()




#
# Gráfica de dispersión - Scatter plot
#

# x = [2015, 2016, 2017, 2018, 2019, 2020, 2021]
# y = [   1,    2,    5,   10,   21,   40,   54]

# plt.scatter(x, y)
# plt.show()


# 
# From Pandas
# 

# np.linspace(0, 10, num=4)

df = pd.read_csv('pandas_notes/netflix_subscription_fee.csv')
# "Country_code"
# "Country"
# "Total Library Size"
# "No. of TV Shows"
# "No. of Movies"
# "Cost Per Month - Basic ($)"
# "Cost Per Month - Standard ($)"
# "Cost Per Month - Premium ($)"

# bins=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
# x = list(sorted(set(df['Cost Per Month - Premium ($)'])))
x = df['Cost Per Month - Premium ($)']
y = df['No. of TV Shows']
plt.scatter(x, y)

plt.xlabel('Cost Per Month - Premium ($)')
plt.ylabel('No. of TV Shows')

plt.show()