from urllib import request, parse, error
from bs4 import BeautifulSoup

html = request.urlopen("http://py4e-data.dr-chuck.net/comments_2016535.html").read()
soup = BeautifulSoup(html, 'html.parser')

tags = soup('span')

total = sum([int(tag.get_text()) for tag in tags])

print("Total: ", total)
