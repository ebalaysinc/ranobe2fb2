import re
from colorama import Fore, Back, Style, just_fix_windows_console

from services.ranobelib import ranobelib_main

# List of services
# name - display name
# regex - regular expression for searching link
# function - entry point
services = [
    {'name': 'RanobeLIB', 'regex': 'ranobelib.me', 'function': ranobelib_main}
]

just_fix_windows_console()

query = input(Fore.YELLOW + "Enter your ranobe link: " + Style.RESET_ALL)

for i in services:
    if len(re.findall(i['regex'], query)) > 0:
        print(Fore.GREEN + 'Service found: ' + i['name'])
        filename = input(Fore.YELLOW + 'Enter filename: ' + Style.RESET_ALL)

        #!!! Entry point always takes the link and the file name
        i['function'](query, filename)
        break

else:
    print(Fore.RED + 'No service found. Aborting' + Style.RESET_ALL)
