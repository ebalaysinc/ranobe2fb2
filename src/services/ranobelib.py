import re
import time
import base64
from log import Logger
from bs4 import BeautifulSoup
from curl_cffi import requests
import xml.etree.ElementTree as ET
from colorama import Fore, Back, Style, just_fix_windows_console

from xml_compose import *
from config import *
from utils import *

just_fix_windows_console()
log = Logger('RanobeLIB')

def ranobelib_main(url, filename): #Точка входа
    slug = re.search(r"(?<=book/)[^?]+", url) # Парсим slug

    if slug:
        slug = slug.group(0)
        log.write(f"Parsed slug: {slug}")

        session = requests.Session()
        headers = {'User-Agent': USER_AGENT, 'Host': 'api.mangalib.me'}
        response = session.get(f"https://api.mangalib.me/api/manga/{slug}?fields[]=summary&fields[]=releaseDate&fields[]=authors",
                                headers=headers)
        log.write(f'Request sended to RanobeLIB API. Status code: {response.status_code}.')

        if response.ok:
            xml = create_root_xml()
            images = {}

            print(Fore.YELLOW + 'Parsing info...' + Style.RESET_ALL)

            json = response.json()['data']
            title_info = {
                "author": [i['name'] for i in json['authors']],
                'book-title': json['rus_name'] if json['rus_name'] != "" else json['name'],
                'annotation': json['summary']
            }
            
            chapters, volumes = get_all_chapters(slug)

            print(Style.DIM + "/"*50 + Style.RESET_ALL)
            print(f"""{Fore.YELLOW}Name: {Style.RESET_ALL}{title_info['book-title']}
{Fore.YELLOW}Volumes: {Style.RESET_ALL}{', '.join(volumes)}
{Fore.YELLOW}Authors: {Style.RESET_ALL}{', '.join(title_info['author'])}
{Fore.YELLOW}Summary: {Style.RESET_ALL}{title_info['annotation']}""")
            print(Style.DIM + "/"*50 + Style.RESET_ALL)

            selected_volumes = input(Fore.YELLOW
                            + 'Enter specific volumes in format "1, 3, 5-7, 9" (or skip if you don\'t care): '
                            + Style.RESET_ALL)
            
            if selected_volumes != "":
                selected_volumes = parse_selected_volumes(selected_volumes)

                if all(volume in volumes for volume in selected_volumes):
                    chapters = filter_volumes(chapters, selected_volumes)
                    title_info['book-title'] = title_info['book-title'] + format_volumes(selected_volumes)
                else:
                    error_message('One of selected volumes doesn\'t exist. Aborting.')
                    return
            #TODO: скачивание отдельных томов

            print('Parsing chapters...')
            content, chapter_images = get_content(slug, chapters, [], {})

            for i in chapter_images.keys():
                try:
                    print(Fore.YELLOW +
                          f'Downloading image {i} ({list(chapter_images.keys()).index(i) + 1}/{len(chapter_images.keys())})' +
                          Style.RESET_ALL, end=' '*40 + '\r')

                    request = requests.get(chapter_images[i])

                    if request.status_code == 429:
                        time_to_sleep = int(response.headers['retry-after']) + 2
                        print(Fore.YELLOW + f'429 Error, waiting {time_to_sleep} seconds' + Style.RESET_ALL, end=' '*15 + '\r')
                        time.sleep(time_to_sleep)
                        request = requests.get(chapter_images[i])

                    if request.ok: images[i] = base64.b64encode(request.content).decode('utf-8')
                    else:
                        print('\n' + Fore.RED + f'{chapter_images[i]} returned {request.status_code}. Skipped' + Style.RESET_ALL)
                except:
                    print('\n' + Fore.RED + f'{chapter_images[i]} can\'t be parsed. Skipped' + Style.RESET_ALL)

            images['cover.jpg'] = base64.b64encode(requests.get(json['cover']['default']).content).decode('utf-8')

            print('\nCleaning content...')
            content = clean_content(content)

            xml = create_description(xml, title_info)
            xml = create_body(xml, content, chapters, title_info)
            xml = create_images(xml, images)

            ET.ElementTree(xml).write("dist/" + filename + '.fb2')

        elif response.status_code == 403:
            error_message("Probably Cloudflare issue. Aborting.")
            return

        elif response.status_code == 404:
            error_message("Title doesn't exist. Aborting.")
            return

        else:
            error_message('Bad status code. Aborting.')
            return

    else: #если slug нельзя спарсить
        error_message("Slug can't be parsed. Probably bad link. Aborting.")
        return

def get_all_chapters(slug):
    session = requests.Session()
    headers = {'User-Agent': USER_AGENT, 'Host': 'api.mangalib.me'}
    response = session.get(f"https://api.mangalib.me/api/manga/{slug}/chapters",
                            headers=headers)
    
    json = response.json()['data']

    log.write(f'Parsed all chapters. Count: {len(json)}')

    chapters = [[
        i['volume'],
        i['number'],
        i['name']
    ] for i in json]

    log.write('\n'.join([
        f'{i[0]}.{i[1]} - {i[2]}' for i in chapters
    ]))

    return chapters, sorted(set(str(i['volume']) for i in json))

def parse_images_from_content(content):
    if type(content) != str: return {}

    soup = BeautifulSoup(content, 'html.parser')
    images = soup.find_all('img')
    src = [img['src'] for img in images if img.get('src')]
    img = {}

    for i in src:
        img[re.search(r'[^/\\&?=]+\.[a-zA-Z0-9]+(?=\?|$)', i).group(0)] = i
    
    return img

def parse_content(response, i, chapter_content, chapter_images):
    json = response.json()['data']

    if type(json['content']) == str:
        chapter_content.append(json['content'])
    else:
        chapter_content.append(convert_json_to_html(json['content']))

    for k in json['attachments']:
        chapter_images[k['filename']] = "https://ranobelib.me" + k['url']
    
    img = parse_images_from_content(json['content'])

    log.write(f"{i[0]}.{i[1]} parsed. Current chapter contents count: {len(chapter_content)}")

    return chapter_content, {**chapter_images, **img}

def get_content(slug, chapters, chapter_content, chapter_images):
    session = requests.Session()
    headers = {'User-Agent': USER_AGENT, 'Host': 'api.mangalib.me'}
    for i in chapters:
        try:
            print(Fore.YELLOW +
                  f'Parsing chapter {i[0]}.{i[1]}. {i[2]} ({chapters.index(i)+1}/{len(chapters)})'
                  + Style.RESET_ALL, end=' '* 50 + '\r')
            response = session.get(f"https://api.mangalib.me/api/manga/{slug}/chapter?number={i[1]}&volume={i[0]}",
                       headers=headers)
            chapter_content, chapter_images = parse_content(response, i,
                          chapter_content, chapter_images)
        except Exception as e:
            time_to_wait = int(response.headers['retry-after']) + 2
            print(Fore.YELLOW + f'429 Error, waiting {time_to_wait} seconds' + Style.RESET_ALL, end=' '*40   + '\r')
            log.write(f'429 Error. Retrying after ' + str(time_to_wait) + " seconds.")
            time.sleep(time_to_wait)

            response = session.get(f"https://api.mangalib.me/api/manga/{slug}/chapter?number={i[1]}&volume={i[0]}",
                       headers=headers)
            chapter_content, chapter_images = parse_content(response, i,
                          chapter_content, chapter_images)

    log.write(f'All chapters successfully parsed. Contents: {len(chapter_content)}. Images: {len(chapter_images)}')
    print() #because end=\r
    return chapter_content, chapter_images

def clean_content(contents):
    cleaned_content = []

    for i in contents:
        soup = BeautifulSoup(i, 'html.parser')
        for k in soup.find_all('p'): # Удаление лишних атрибутов
            if 'data-paragraph-index' in k.attrs:
                del k.attrs['data-paragraph-index']

        for l in soup.find_all('img'): # Замена img на image и изменение l:href

            if l.attrs != None and l.attrs['src'] != "": #Если img по каким-то причинам пуст, то скипаем
                image = soup.new_tag('image', attrs={'l:href': '#' + re.search(r"[^/]+\.\w+$", l.attrs['src']).group()})
                parent = l.parent

                if type(parent) == BeautifulSoup: #если глава состоит из одних картинок, <p></p> отсутствует, и родителем является BeautifulSoup
                    l.decompose()
                    parent.append(image)

                else:
                    parent.insert_before(image)

                    parent.decompose()

        for e in soup.findAll('br'): # Замена br на empty-line
            e.name = 'empty-line'

        cleaned_content.append(str(soup))
    
    return cleaned_content

def convert_json_to_html(content):
    soup = BeautifulSoup()

    for i in content['content']:
        if i['type'] == 'paragraph':
            p = soup.new_tag('p')

            if 'content' in i.keys():
                text = i['content'][0]
                if 'marks' in text.keys():
                    edited_p = p
                    for k in text['marks']:
                        if k['type'] == 'bold':
                            element = soup.new_tag('b')
                        if k['type'] == 'italic':
                            element = soup.new_tag('i')
                            
                        edited_p.append(element)
                        edited_p = element
                    edited_p.string = i['content'][0]['text']
                else:
                    p.string = i['content'][0]['text']

            soup.append(p)
        else:
            if 'attrs' in i.keys() and 'images' in i['attrs'].keys():
                image = soup.new_tag('image')
                image.attrs['l:href'] = '#' + i['attrs']['images'][0]['image'] + '.jpg'

                soup.append(image)
            else:
                soup.append(soup.new_tag('p'))
    
    return str(soup)