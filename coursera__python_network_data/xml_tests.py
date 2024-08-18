from urllib import request
import xml.etree.ElementTree as ET

url = input('URL: ')
data = request.urlopen(url).read()

tree = ET.fromstring(data)


total = sum([int(comment.find('count').text) for comment in tree.findall('comments/comment')])
print('Total: ', total)
