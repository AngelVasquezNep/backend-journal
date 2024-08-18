import re
import ssl
import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup


# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = input("Enter URL: ")
count = int(input("Enter count: "))
position = int(input("Enter position: ")) - 1 # Index based

def get_link_by_position(url, position, count):
    urls = urls_from(url)
    next_url = urls[position]
    print(f'{url=} | {position=} | {count=} | {next_url=}')
    if count == 0:
        return url
    return get_link_by_position(next_url, position, count - 1)


def urls_from(url):
    html = urllib.request.urlopen(url, context=ctx).read()
    soup = BeautifulSoup(html, 'html.parser')
    return [tag.get('href') for tag in soup('a')]


result = get_link_by_position(url, position, count)
name = re.findall(r'known_by_(\w+)\.html', result)[0]

print("RESULT: ", name)
