import colorama

colorama.just_fix_windows_console()

def error_message(message):
    print(colorama.Fore.RED + message + colorama.Style.RESET_ALL)

def parse_selected_volumes(input_string):
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

def filter_volumes(book_chapters, selected_volumes):
    return [chapter for chapter in book_chapters if chapter[0] in selected_volumes]

def format_volumes(volumes):
    if len(volumes) == 1:
        return f' (Том {volumes[0]})'
    else:
        return f' (Тома {volumes[0]}-{volumes[-1]})'