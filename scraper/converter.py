import multiprocessing
import os
import re
from multiprocessing import Pool

from bs4 import BeautifulSoup
from click import echo

from scraper.const import CHAPTER_DOC
from scraper.manifest import Manifest
from scraper.generator import ElementNotFoundException


class Converter:
    def __init__(self, config):
        self.files = config.files
        self.selectors = config.selectors
        self.substitutions = config.substitutions
        self.remove_empty_elements = config.remove_empty_elements
        self.manifest = Manifest(config.files.manifest_file)

    def convert(self, doc, url, title):
        soup = BeautifulSoup(doc, "lxml")

        content_el = soup.select_one(self.selectors.content_element)

        if not content_el:
            raise ElementNotFoundException("Content element not found")

        if s := self.selectors.get("cut_off_element"):
            last_p_el = content_el.select_one(s)
            if not last_p_el:
                raise ElementNotFoundException()
            last_p_el = last_p_el.find_previous_sibling()
        else:
            last_p_el = content_el.select_one("p:last-of-type")

        # Delete everything after the last paragraph
        while last_p_el.find_next_sibling():
            last_p_el.find_next_sibling().decompose()

        for el in content_el.findChildren():
            if self.remove_empty_elements and el.get_text().strip() == "":
                el.decompose()

        for s in [s for s in self.substitutions if s.selector_type == "css"]:
            if s.chapter_url != url:
                continue

            els = content_el.select(s.selector)
            for el in els:
                if s.replace_with:
                    el.replace_with(s.replace_with)
                else:
                    el.decompose()

        content_el.name = "body"
        del content_el["class"]
        content_el.insert(0, soup.new_tag("h1"))
        content_el.h1.append(title)

        doc = BeautifulSoup(CHAPTER_DOC, "lxml")
        doc.head.append(doc.new_tag("title"))
        doc.head.title.append(title)
        doc.body.replace_with(content_el)

        doc = str(doc)
        for s in self.substitutions:
            if s.selector_type == "text":
                doc = doc.replace(s.selector, s.replace_with)
            elif s.selector_type == "regex":
                doc = re.sub(r"%s" % s.selector, s.replace_with, doc)

        echo("Converted chapter %s" % title)

        return doc

    def convert_file(self, path, converted_path, url, title):
        if os.path.isfile(path):
            with open(path, "r", encoding="utf8") as file:
                doc = file.read()
            with open(converted_path, "w", encoding="utf8") as file:
                doc = str(self.convert(doc, url, title))
                file.write(doc)
        else:
            raise FileNotFoundError()

    def _convert_helper(self, e):
        index = e[0]
        chapter = e[1]
        if not chapter.get("converted"):
            self.convert_file(
                os.path.join(self.files.cache_folder, chapter.get("file")),
                os.path.join(self.files.book_folder, chapter.get("file")),
                chapter.get("url"),
                chapter.get("title")
            )
            # TODO: this doesn't work
            self.manifest[index].update({"converted": True})
            self.manifest.save()

    def convert_all(self):
        pool = Pool(multiprocessing.cpu_count())
        pool.map(self._convert_helper, enumerate(self.manifest))

        for i in range(len(self.manifest)):
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
