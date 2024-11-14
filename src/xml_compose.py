import uuid
import datetime
from log import Logger
import xml.etree.ElementTree as ET

log = Logger('XML Composer')

def create_root_xml():
    root = ET.Element('FictionBook')
    root.attrib['xmlns:'] = "http://www.gribuser.ru/xml/fictionbook/2.0"
    root.attrib['xmlns:l'] = "http://www.w3.org/1999/xlink"

    return root

def create_description(root: ET.Element, t_info):
    description = ET.SubElement(root, 'description')
    title_info = ET.SubElement(description, 'title-info')
    document_info = ET.SubElement(description, 'document-info')

    ET.SubElement(title_info, 'genre').text = 'sf_history'
    for i in t_info['author']:
        ET.SubElement(ET.SubElement(title_info, 'author'), 'nickname').text = i
    ET.SubElement(title_info, 'book-title').text = t_info['book-title']
    coverpage = ET.SubElement(title_info, 'coverpage')
    coverimage = ET.SubElement(coverpage, 'image')
    coverimage.attrib['l:href'] = '#cover.jpg'
    ET.SubElement(title_info, 'lang').text = 'ru'
    ET.SubElement(title_info, 'annotation').text = t_info['annotation']

    ET.SubElement(document_info, 'author').text = 'Ranobe2FB2 User'
    ET.SubElement(document_info, 'program-used').text = 'Ranobe2FB2'
    date = ET.SubElement(document_info, 'date')
    date.attrib['value'] = datetime.datetime.now().strftime("%Y-%m-%d")
    date.text = datetime.datetime.now().strftime("%d.%m.%Y")
    ET.SubElement(document_info, 'id').text = str(uuid.uuid4()).upper()
    ET.SubElement(document_info, 'version').text = '1'

    log.write("Saved basic description")
    return root

def create_images(root, images):
    for i in images.keys():
        bin = ET.SubElement(root, 'binary')
        bin.attrib['id'] = i
        bin.attrib['content-type'] = 'image/jpeg'
        bin.text = images[i]
        log.write(f'Saved image {i}')
    return root