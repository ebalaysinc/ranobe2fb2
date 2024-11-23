import uuid
import datetime
from log import Logger
from typing import Mapping, List
import xml.etree.ElementTree as ET

log = Logger('XML Composer')

def create_root_xml() -> ET.Element:
    """
    Creating root of XML

    Returns:
        ET.Element
    """
    root = ET.Element('FictionBook')
    root.attrib['xmlns:'] = "http://www.gribuser.ru/xml/fictionbook/2.0"
    root.attrib['xmlns:l'] = "http://www.w3.org/1999/xlink"

    return root

def create_description(root: ET.Element, t_info: Mapping[str, str]) -> ET.Element:
    """
    Creating description in XML

    title_info:
        author (List[str]): list of author nicknames
        book-title (str): the book title
        annotation (str): the book annotation (summary)

    Args:
        root (ET.Element): XML root
        t_info: information about title
    
    Returns:
        ET.Element: updated XML root
    """

    description = ET.SubElement(root, 'description')
    title_info = ET.SubElement(description, 'title-info')
    document_info = ET.SubElement(description, 'document-info')

    ET.SubElement(title_info, 'genre').text = 'sf_history' # Setting the genre

    for i in t_info['author']: #Setting authors
        ET.SubElement(ET.SubElement(title_info, 'author'), 'nickname').text = i
    
    ET.SubElement(title_info, 'book-title').text = t_info['book-title'] # Setting the book title

    # Setting the cover
    coverpage = ET.SubElement(title_info, 'coverpage')
    coverimage = ET.SubElement(coverpage, 'image')
    coverimage.attrib['l:href'] = '#cover.jpg'

    ET.SubElement(title_info, 'lang').text = 'ru' # Setting language
    ET.SubElement(title_info, 'annotation').text = t_info['annotation'] # Setting annotation

    # Setting technical information

    ET.SubElement(document_info, 'author').text = 'Ranobe2FB2 User'
    ET.SubElement(document_info, 'program-used').text = 'Ranobe2FB2'

    date = ET.SubElement(document_info, 'date')
    date.attrib['value'] = datetime.datetime.now().strftime("%Y-%m-%d")
    date.text = datetime.datetime.now().strftime("%d.%m.%Y")

    ET.SubElement(document_info, 'id').text = str(uuid.uuid4()).upper()
    ET.SubElement(document_info, 'version').text = '1'


    log.write("Saved basic description")
    return root

def create_images(root: ET.Element, images: Mapping[str, str]) -> ET.Element:
    """
    Addings all images into XML root.

    Args:
        root (ET.Element): XML root
        images (Mapping[str, str]): dictionary with image name and Base64
    
    Returns:
        ET.Element: updated root
    """

    for i in images.keys():
        bin = ET.SubElement(root, 'binary')

        bin.attrib['id'] = i
        bin.attrib['content-type'] = 'image/jpeg'
        bin.text = images[i]

        log.write(f'Saved image {i}')
    return root

def create_body(root: ET.Element, content: List[str], chapters: List[List[str]], title_info: Mapping[str, str]) -> ET.Element:
    """
    Fills main body with content

    Args:
        root (ET.Element): XML root
        content (List[str]): list of XML content (1 content - 1 chapter)
        chapters (List[List[str]]): list of chapters
        title_info (Mapping[str, str]): information about title 

    Returns:
        ET.Element: updated root
    """

    body = ET.SubElement(root, 'body')
    title = ET.SubElement(body, 'title')
    ET.SubElement(title, 'p').text = title_info["book-title"]

    for i in range(len(content)):
        section = ET.SubElement(body, 'section')
        section_title = f'{chapters[i][0]}.{chapters[i][1]}. {chapters[i][2]}'

        ET.SubElement(ET.SubElement(section, 'title'), 'p').text = section_title

        text = ET.ElementTree(ET.fromstring(
            "<root xmlns:l=\"http://www.w3.org/1999/xlink\">" + content[i] + "</root>"
        )).getroot()

        for element in text:
            section.append(element)

        log.write('Section created: ' + section_title)

    return root
