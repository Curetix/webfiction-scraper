import os
import re
import sys
from multiprocessing import Pool, cpu_count

from bs4 import BeautifulSoup
from bs4.element import Tag
from click import echo

from .manifest import Manifest
from .const import CHAPTER_DOC, DATA_DIR
from .exception import ElementNotFoundException

# Append the data dir to path if it contains the chapter_fixes.py file
if os.path.isfile(os.path.join(DATA_DIR, "chapter_fixes.py")):
    sys.path.insert(0, DATA_DIR)

from chapter_fixes import apply_chapter_fix


class Converter:
    def __init__(self, config):
        self.files = config.files
        self.selectors = config.selectors
        self.substitutions = config.substitutions
        self.remove_empty_elements = config.remove_empty_elements
        self.manifest = Manifest(config.files.manifest_file)

    def convert(self, doc, chapter):
        title = chapter.get("title")
        soup = BeautifulSoup(doc, "lxml")

        content_el = soup.select_one(self.selectors.content_element)

        if not content_el:
            raise ElementNotFoundException("Content element not found for chapter: " + title)

        content_el = apply_chapter_fix(chapter, soup, content_el)

        last_p_el = content_el.select_one(self.selectors.content_element + " > p:last-of-type")

        if not last_p_el:
            raise ElementNotFoundException("Last paragraph not found for chapter: " + title)

        # If a cut-off element is specified, set its previous sibling as last element, otherwise the last paragraph
        if s := self.selectors.get("cut_off_element"):
            if type(s) == str:
                s = [s]

            for e in s:
                last_p_el = content_el.select_one(e)
                if last_p_el:
                    last_p_el = last_p_el.find_previous_sibling()
                    break

        # Delete everything after the last element
        while last_p_el.find_next_sibling():
            last_p_el.find_next_sibling().decompose()

        # Remove empty elements if enabled
        if self.remove_empty_elements:
            for el in content_el.find_all(recursive=False):
                if el.get_text().strip() == "":
                    el.decompose()

        # Apply substitutions with CSS selector
        for s in [s for s in self.substitutions if s.selector_type == "css"]:
            if s.chapter_url and s.chapter_url != chapter.get("url"):
                continue

            els = content_el.select(s.selector)
            for el in els:
                if s.replace_with:
                    el.replace_with(s.replace_with)
                else:
                    el.decompose()

        # Change the content elements tag to <body> and add the chapter title
        content_el.name = "body"
        del content_el["class"]
        content_el.insert(0, soup.new_tag("h1"))
        content_el.h1.append(title)

        # Create the output document and add the body
        doc = BeautifulSoup(CHAPTER_DOC, "lxml")
        doc.head.append(doc.new_tag("title"))
        doc.head.title.append(title)
        doc.body.replace_with(content_el)

        # Apply text and regex substitutions
        doc = str(doc)
        for s in self.substitutions:
            if s.selector_type == "text":
                doc = doc.replace(s.selector, s.replace_with)
            elif s.selector_type == "regex":
                doc = re.sub(r"%s" % s.selector, s.replace_with, doc)

        echo("Converted chapter: %s" % title)

        return doc

    @staticmethod
    def apply_chapter_fix(chapter, soup, content_el):
        def fix_nothing():
            pass

        def fix_metaworld_chronicles_paragraphs():
            """Some chapters have <div> elements instead of proper <p> paragraphs, so rename all <div> tags to <p>"""
            for el in content_el.find_all("div", recursive=False):
                el.name = "p"

        def fix_metaworld_chronicles_single_div():
            div_el = content_el.select_one("div")
            for e in div_el.contents:
                if type(e) is Tag and e.name == "br":
                    continue
                new_p = soup.new_tag("p")
                content_el.append(new_p)
                content_el.append("\n")
                content_el.select_one("p:last-of-type").append(e)
            div_el.decompose()

        fixes = {
            "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/494392/chapter-346-bride-and-groom": fix_metaworld_chronicles_paragraphs,
            "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/541710/chapter-368-even-death-may-die": fix_metaworld_chronicles_paragraphs,
            "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/551476/chapter-372-a-little-knowledge": fix_metaworld_chronicles_paragraphs,
            "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/553925/chapter-373-the-burden-of-knowledge": fix_metaworld_chronicles_single_div,
        }

        fixes.get(chapter.get("url"), fix_nothing)()

        return content_el

    def convert_file(self, index, chapter):
        in_file = os.path.join(self.files.cache_folder, chapter.get("file"))
        out_file = os.path.join(self.files.book_folder, chapter.get("file"))

        if os.path.isfile(in_file):
            with open(in_file, "r", encoding="utf8") as file:
                doc = file.read()
            with open(out_file, "w", encoding="utf8") as file:
                try:
                    doc = self.convert(doc, chapter)
                except ElementNotFoundException as e:
                    echo(e)
                    sys.exit()
                file.write(doc)
        else:
            echo("File %s not found" % in_file)
            sys.exit()

        return index

    def convert_all(self):
        with Pool(processes=cpu_count()) as pool:
            chapters_to_convert = filter(lambda t: not t[1].get("converted"), enumerate(self.manifest))
            results = [pool.apply_async(self.convert_file, args=m) for m in chapters_to_convert]
            converted_chapters = [p.get() for p in results]

        for i in converted_chapters:
            self.manifest[i].update({"converted": True})

        self.manifest.save()

        echo("Converted all chapters!")

    def clean(self):
        import shutil
        shutil.rmtree(self.files.book_folder)
        os.mkdir(self.files.book_folder)

        for i in range(len(self.manifest)):
            self.manifest[i].update({"converted": False})

        self.manifest.save()
