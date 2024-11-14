import re
import time
import base64
import xml.etree
from log import Logger
from bs4 import BeautifulSoup
from curl_cffi import requests
import xml.etree.ElementTree as ET
import xml.etree

from xml_compose import *
from config import *

log = Logger('RanobeLIB')

def ranobelib_download(url, filename):
    slug = re.search(r"(?<=book/)[^?]+", url)

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

            print('Parsing info...')
            json = response.json()['data']
            title_info = {
                "author": [i['name'] for i in json['authors']],
                'book-title': json['rus_name'],
                'annotation': json['summary']
            }
            
            volume = input('Enter your volume if you want one certain volume (or enter 0 if you don\'t care): ')
            #TODO: скачивание отдельных томов

            print('Parsing chapters...')
            chapters = get_all_chapters(slug)
            content, chapter_images = get_content(slug, chapters, [], {})

            for i in chapter_images.keys():
                images[i] = base64.b64encode(requests.get(chapter_images[i]).content).decode('utf-8')

            images['cover.jpg'] = base64.b64encode(requests.get(json['cover']['default']).content).decode('utf-8')

            if type(content[0]) == str: # Как я понимаю, что-то написано на html, а что-то хранится в json
                html = True
            else:
                html = False
            
            print('Mode: ' + 'HTML' if html else 'JSON')
            log.write(f'html: {html}')

            if not html:
                print('JSON is not supported now. Aborting.')
                return

            print('Cleaning content...')
            if html:
                content = clean_content(content)

            xml = create_description(xml, title_info)
            xml = create_body(xml, content, chapters, title_info)
            xml = create_images(xml, images)

            ET.ElementTree(xml).write(filename + '.fb2')
            # with open(filename + '.fb2', 'w') as f:
                # f.write()

        elif response.status_code == 403:
            print("Probably Cloudflare issue. Aborting.")
            return

        else:
            print('Bad status code. Aborting.')
            return

    else:
        print("Slug can't be parsed. Probably bad link. Aborting.")
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

    return chapters

def parse_images_from_content(content):
    soup = BeautifulSoup(content, 'html.parser')
    images = soup.find_all('img')
    src = [img['src'] for img in images if img.get('src')]
    img = {}

    for i in src:
        img[re.search(r'[^/\\&?=]+\.[a-zA-Z0-9]+(?=\?|$)', i).group(0)] = i
    
    return img

def parse_content(response, i, chapter_content, chapter_images):
    json = response.json()['data']
    chapter_content.append(json['content'])
    for k in json['attachments']:
        chapter_images[k['filename']] = "https://api.ranobelib.me" + k['url']
    
    img = parse_images_from_content(json['content'])

    log.write(f"{i[0]}.{i[1]} parsed. Current chapter contents count: {len(chapter_content)}")

    return chapter_content, {**chapter_images, **img}

def get_content(slug, chapters, chapter_content, chapter_images):
    session = requests.Session()
    headers = {'User-Agent': USER_AGENT, 'Host': 'api.mangalib.me'}
    for i in chapters:
        try:
            response = session.get(f"https://api.mangalib.me/api/manga/{slug}/chapter?number={i[1]}&volume={i[0]}",
                       headers=headers)
            chapter_content, chapter_images = parse_content(response, i,
                          chapter_content, chapter_images)
        except Exception as e:
            time_to_wait = int(response.headers['retry-after']) + 2
            print(f'429 Error. Retrying after ' + str(time_to_wait) + " seconds.")
            log.write(f'429 Error. Retrying after ' + str(time_to_wait) + " seconds.")
            time.sleep(time_to_wait)

            response = session.get(f"https://api.mangalib.me/api/manga/{slug}/chapter?number={i[1]}&volume={i[0]}",
                       headers=headers)
            chapter_content, chapter_images = parse_content(response, i,
                          chapter_content, chapter_images)

    log.write(f'All chapters successfully parsed. Contents: {len(chapter_content)}. Images: {len(chapter_images)}')
    return chapter_content, chapter_images

def clean_content(contents):
    cleaned_content = []

    for i in contents:
        soup = BeautifulSoup(i, 'html.parser')
        for k in soup.find_all('p'): # Удаление лишних атрибутов
            if 'data-paragraph-index' in k.attrs:
                del k.attrs['data-paragraph-index']

        for l in soup.find_all('img'): # Удаление атрибутов и изменение href 
            # TODO: сделать замену </img> на <img></img> 
            # ../logs/log2024-11-12-21-58-57.txt:499

            if l.attrs != None:
                attrs = {
                'l:href': '#' + re.search(r"[^/]+\.\w+$", l.attrs['src']).group()
                }
                image = soup.new_tag('image', attrs=attrs)
                parent = l.parent
                parent.insert_before(image)

                parent.decompose()


            # if 'loading' in l.attrs:
            #     del l.attrs['loading']
            # if 'src' in l.attrs:
            #     del l.attrs['src']

        
        for e in soup.findAll('br'): # Смена br на empty-line
            e.name = 'empty-line'

        cleaned_content.append(str(soup))
    
    return cleaned_content

def create_body(root: ET.Element, content, chapters, t_info):
    body = ET.SubElement(root, 'body')
    title = ET.SubElement(body, 'title')
    ET.SubElement(title, 'p').text = t_info["book-title"]

    for i in range(len(content)):
        section = ET.SubElement(body, 'section')
        section_title = f'{chapters[i][0]}.{chapters[i][1]}. {chapters[i][2]}'
        ET.SubElement(ET.SubElement(section, 'title'), 'p').text = section_title

        # log.write(content[i])
        text = ET.ElementTree(ET.fromstring("<root xmlns:l=\"http://www.w3.org/1999/xlink\">" + content[i] + "</root>")).getroot()
        for element in text:
            section.append(element)

        log.write('Section created: ' + section_title)

    return root
