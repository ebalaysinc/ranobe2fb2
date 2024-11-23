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

def ranobelib_main(url, filename): #Entry point
    slug = re.search(r"(?<=book/)[^?]+", url) # Parsing slug

    if slug:
        slug = slug.group(0)
        log.write(f"Parsed slug: {slug}")

        response = get_request(f"https://api.mangalib.me/api/manga/{slug}?fields[]=summary&fields[]=releaseDate&fields[]=authors")
        log.write(f'Request sended to RanobeLIB API. Status code: {response.status_code}.')

        if response.ok:
            # Creating a base

            xml = create_root_xml()
            images = {}

            print(Fore.YELLOW + 'Parsing info...' + Style.RESET_ALL)

            json = response.json()['data']
            title_info = {
                "author": [i['name'] for i in json['authors']],
                'book-title': json['rus_name'] if json['rus_name'] != "" else json['name'],
                'annotation': json['summary']
            }
            
            chapters, volumes = get_all_chapters(slug) # Getting all chapters

            # Printing info

            print(Style.DIM + "/"*50 + Style.RESET_ALL)
            print(f"""{Fore.YELLOW}Name: {Style.RESET_ALL}{title_info['book-title']}
{Fore.YELLOW}Volumes: {Style.RESET_ALL}{', '.join(volumes)}
{Fore.YELLOW}Authors: {Style.RESET_ALL}{', '.join(title_info['author'])}
{Fore.YELLOW}Summary: {Style.RESET_ALL}{title_info['annotation']}""")
            print(Style.DIM + "/"*50 + Style.RESET_ALL)

            # Volume selector

            selected_volumes = input(Fore.YELLOW
                            + 'Enter specific volumes in format "1, 3, 5-7, 9" (or skip if you don\'t care): '
                            + Style.RESET_ALL)
            
            if selected_volumes != "": # If volume selected
                selected_volumes = parse_selected_volumes(selected_volumes)

                if all(volume in volumes for volume in selected_volumes):
                    chapters = filter_volumes(chapters, selected_volumes)
                    title_info['book-title'] = title_info['book-title'] + format_volumes(selected_volumes)
                
                else:
                    error_message('One of selected volumes doesn\'t exist. Aborting.')
                    return


            print('Parsing chapters...')
            content, chapter_images = get_content(slug, chapters)

            # Downloading all images
            images = download_images(chapter_images, json['cover']['default'])

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

    else: #if there no slug
        error_message("Slug can't be parsed. Probably bad link. Aborting.")
        return

def get_all_chapters(slug: str):
    """
    Getting all chapters

    Args:
        slug (str): slug
    Returns:
        chapters (List[List[str]]):
        volumes (List[str]):
    """
    response = get_request(f"https://api.mangalib.me/api/manga/{slug}/chapters")
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

    return chapters, sorted(set(str(i['volume']) for i in json), key=int)

def parse_images_from_content(content) -> Mapping[str, str]:
    """
    Parsing images from content

    Args:
        content (str): HTML content
    Returns:
        Mapping[str, str]
    """
    if type(content) != str: return {} # If not HTML

    soup = BeautifulSoup(content, 'html.parser')
    images = soup.find_all('img')
    src = [img['src'] for img in images if img.get('src')]
    img = {}

    for i in src:
        img[re.search(r'[^/\\&?=]+\.[a-zA-Z0-9]+(?=\?|$)', i).group(0)] = i
    
    return img

def parse_content(data: Mapping, chapter: List[str], chapter_content, chapter_images):
    """
    Parsing content into XML

    Args:
        data (Mapping): response from server
        chapter (List[str]): info about chapter
    Returns:
        chapter_content (List[str]):
        (Mapping[str: str]):
    """

    if type(data['content']) == str: # If HTML
        chapter_content.append(data['content'])
    else:
        chapter_content.append(convert_json_to_html(data['content']))

    for k in data['attachments']:
        chapter_images[k['filename']] = "https://ranobelib.me" + k['url']
    
    img = parse_images_from_content(data['content'])

    log.write(f"{chapter[0]}.{chapter[1]} parsed. Current chapter contents count: {len(chapter_content)}")

    return chapter_content, {**chapter_images, **img}

def get_content(slug: str, chapters: List[List[str]]):
    """
    Getting content from chapters
    
    Args:
        slug (str): slug
        chapters (List[List[str]]): chapters to get content
    Returns:
        chapter_content (List[str]):
        chapter_images (Mapping[str]):
    """

    chapter_content, chapter_images = [], {}

    for i in chapters:
        print(Fore.YELLOW +
              f'Parsing chapter {i[0]}.{i[1]}. {i[2]} ({chapters.index(i)+1}/{len(chapters)})'
              + Style.RESET_ALL, end=' '* 50 + '\r')
        
        response = get_request(f"https://api.mangalib.me/api/manga/{slug}/chapter?number={i[1]}&volume={i[0]}")

        if response.status_code == 429:
            time_to_wait = int(response.headers['retry-after']) + 2

            print(Fore.YELLOW + f'429 Error, waiting {time_to_wait} seconds' + Style.RESET_ALL, end=' '*40   + '\r')
            log.write(f'429 Error. Retrying after ' + str(time_to_wait) + " seconds.")
            time.sleep(time_to_wait)

            response = get_request(f"https://api.mangalib.me/api/manga/{slug}/chapter?number={i[1]}&volume={i[0]}")
        
        chapter_content, chapter_images = parse_content(response.json()['data'], i,
                                                        chapter_content, chapter_images)
        

    log.write(f'All chapters successfully parsed. Contents: {len(chapter_content)}. Images: {len(chapter_images)}')
    print() #because end=\r
    return chapter_content, chapter_images

def clean_content(contents: List[str]) -> List[str]:
    """
    Converting HTML into XML by cleaning it from some things

    Args:
        contents (List[str]): list of contents
    Returns:
        List[str]: list of cleaned content
    """

    cleaned_content = []

    for i in contents:
        soup = BeautifulSoup(i, 'html.parser')

        for k in soup.find_all('p'): # Deleting extra tags
            if 'data-paragraph-index' in k.attrs:
                del k.attrs['data-paragraph-index']

        for l in soup.find_all('img'): # Replacing img to image and changing parent and l:href
            if l.attrs != None and l.attrs['src'] != "": #Skip if img somewhy don't have src
                image = soup.new_tag('image', attrs={'l:href': '#' + re.search(r"[^/]+\.\w+$", l.attrs['src']).group()})
                parent = l.parent

                # If there no <p> and only images with BeautifulSoup parent
                if type(parent) == BeautifulSoup: 
                    l.decompose()
                    parent.append(image)
                else:
                    parent.insert_before(image)
                    parent.decompose()

        for e in soup.findAll('br'): # Changing br to empty-line
            e.name = 'empty-line'

        cleaned_content.append(str(soup))
    
    return cleaned_content

def convert_json_to_html(content: Mapping) -> str:
    """
    Converting JSON Content to HTML

    Args:
        content (Mapping): content
    Returns:
        str: HTML
    """

    soup = BeautifulSoup() # Creating root

    for i in content['content']:
        if i['type'] == 'paragraph': # If paragraph
            p = soup.new_tag('p')

            if 'content' in i.keys(): # If it have content
                text = i['content'][0]
                if 'marks' in text.keys(): # Checking for marks
                    edited_p = p
                    for k in text['marks']:

                        if k['type'] == 'bold': element = soup.new_tag('b')
                        if k['type'] == 'italic': element = soup.new_tag('i')
                            
                        edited_p.append(element)
                        edited_p = element
                    edited_p.string = i['content'][0]['text']
                
                else: p.string = i['content'][0]['text']

            soup.append(p)
        else: # If image (or something else)
            if 'attrs' in i.keys() and 'images' in i['attrs'].keys(): #If it have image
                image = soup.new_tag('image')
                image.attrs['l:href'] = '#' + i['attrs']['images'][0]['image'] + '.jpg'

                soup.append(image)
            else:
                soup.append(soup.new_tag('p'))
    
    return str(soup)

def download_images(chapter_images: List[str], cover: str) -> Mapping[str, str]:
    """
    Downloading all images from chapter_images and converting it into Base64

    Args:
        chapter_images (List[str]): list of images
        cover (str): link to the book cover
    Returns:
        Mapping[str, str]: dictionary of image names and images
    """
    images = {}

    for i in chapter_images.keys():
        try:
            print(Fore.YELLOW +
                    f'Downloading image {i} ({list(chapter_images.keys()).index(i) + 1}/{len(chapter_images.keys())})' +
                    Style.RESET_ALL, end=' '*40 + '\r')

            request = get_request(chapter_images[i])

            if request.status_code == 429:
                time_to_sleep = int(request.headers['retry-after']) + 2
                print(Fore.YELLOW + f'429 Error, waiting {time_to_sleep} seconds' + Style.RESET_ALL, end=' '*15 + '\r')
                time.sleep(time_to_sleep)

                request = get_request(chapter_images[i])

            if request.ok: images[i] = base64.b64encode(request.content).decode('utf-8')
            else:
                print('\n' + Fore.RED + f'{chapter_images[i]} returned {request.status_code}. Skipped\n' + Style.RESET_ALL)
        
        except Exception as e:
            print('\n' + Fore.RED + f'{chapter_images[i]} can\'t be parsed. Skipped\n' + Style.RESET_ALL)

    images['cover.jpg'] = base64.b64encode(get_request(cover).content).decode('utf-8')
    
    return images