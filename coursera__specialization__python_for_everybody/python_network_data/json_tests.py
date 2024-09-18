import json
from urllib import request

url = input('URL ')
data = json.loads(request.urlopen(url).read())

total = sum([int(comment.get('count')) for comment in data.get('comments')])

print('TOTAL: ', total)
