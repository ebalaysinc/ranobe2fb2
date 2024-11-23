from colorama import Fore, Back, Style, just_fix_windows_console
from curl_cffi import requests
from typing import List, Mapping

from config import USER_AGENT

just_fix_windows_console()

def error_message(message: str) -> None:
    print(Fore.RED + message + Style.RESET_ALL)


def parse_selected_volumes(input_string: str) -> List[str]:
    """
    Volume parser from query like "1, 3, 5-7, 9" into list of numbers

    Args:
        input_string (str): query
    Returns:
        List[str]: list of numbers
    """

    try:
        volumes = set()
        parts = input_string.split(',')

        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                volumes.update(str(i) for i in range(start, end + 1))
            else:
                volumes.add(part)

        return sorted(volumes, key=int)

    except:
        return ['just some shit for dropping error']

def filter_volumes(book_chapters: List[List[str]], selected_volumes: List[str]) -> List[List[str]]:
    """
    Filters chapters, leaving only from selected volumes

    Args:
        book_chapters (List[List[str]]): list of chapters
        selected_volumes (List[str]): list of selected volumes
    Returns:
        List[List[str]]: list of selected chapters
    """

    return [chapter for chapter in book_chapters if chapter[0] in selected_volumes]

def format_volumes(volumes: str) -> str:
    """
    Formats list of volumes for book title
    """

    if len(volumes) == 1:
        return f' (Том {volumes[0]})'
    else:
        return f' (Тома {volumes[0]}-{volumes[-1]})'

def get_request(url: str, headers: Mapping[str, str] = {}) -> requests.Response:
    """
    Function for sending request and getting response (to simplify code)
    """
    with requests.Session() as session:
        return session.get(url, headers={'User-Agent': USER_AGENT, **headers})
