import re

from services.ranobelib import ranobelib_download

services = [
    {'name': 'RanobeLIB', 'regex': 'ranobelib.me', 'function': ranobelib_download}
]

query = input("Enter your ranobe link: ")
for i in services:
    if len(re.findall(i['regex'], query)) > 0:
        print('Service found: ' + i['name'])
        filename = input('Enter filename: ')
        i['function'](query, filename)
        break
else:
    print('No service found. Aborting')