import os

from bs4 import BeautifulSoup

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

    def convert(self, soup, url, title):
        doc = BeautifulSoup(CHAPTER_DOC, "lxml")
        doc.head.append(doc.new_tag("title"))
        doc.head.title.append(title)

        content_el = soup.select_one(self.selectors.content_element)
        content_el.name = "body"
        del content_el["class"]
        content_el.insert(0, soup.new_tag("h1"))
        content_el.h1.append(title)

        if not content_el:
            raise ElementNotFoundException("Content element not found")

        last_p_el = content_el.select_one("p:last-of-type")

        # Delete everything after the last paragraph
        while last_p_el.find_next_sibling():
            last_p_el.find_next_sibling().decompose()

        for el in content_el.findChildren():
            if self.remove_empty_elements and el.get_text().strip() == "":
                el.decompose()

        # for s in self.substitutions:
        #     if s.get("chapterUrl") and s.get("chapterUrl") != url:
        #         continue
        #
        #     if s.get("css"):
        #         els = content_el.select(s.get("css"))
        #         for el in els:
        #             pass

        doc.body.replace_with(content_el)

        return doc

    def convert_file(self, path, converted_path, url, title):
        if os.path.isfile(path):
            with open(path, "r", encoding="utf8") as file:
                doc = file.read()
                soup = BeautifulSoup(doc, "lxml")
            with open(converted_path, "w", encoding="utf8") as file:
                doc = str(self.convert(soup, url, title))
                file.write(doc)
        else:
            raise FileNotFoundError()

    def convert_all(self):
        for (i, f) in enumerate(self.manifest):
            if not f.get("converted"):
                self.convert_file(
                    os.path.join(self.files.cache_folder, f.get("file")),
                    os.path.join(self.files.book_folder, f.get("file")),
                    f.get("url"),
                    f.get("title")
                )
                self.manifest[i].update({"converted": True})

    def clean(self):
        import shutil
        shutil.rmtree(self.files.book_folder)
        os.mkdir(self.files.book_folder)

        for (i, e) in self.manifest:
            self.manifest[i].update({"converted": False})
        self.manifest.save()
