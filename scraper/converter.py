import os
import re
from multiprocessing import Pool, cpu_count

from bs4 import BeautifulSoup
from click import echo

from .manifest import Manifest
from .const import CHAPTER_DOC
from .exception import ElementNotFoundException

from .chapter_fixes import CHAPTER_FIXES, unwrap_toplevel_divs


class Converter:
    def __init__(self, config):
        self.files = config.files
        self.selectors = config.selectors
        self.substitutions = config.substitutions
        self.remove_empty_elements = config.remove_empty_elements
        self.skip_urls = config.skip_urls
        self.skip_conversion = config.skip_conversion
        self.manifest = Manifest(config.files.manifest_file)

    def convert(self, doc, chapter):
        title = chapter.get("title")
        soup = BeautifulSoup(doc, "html.parser")

        content_el = soup.select_one(self.selectors.content_element)

        if not content_el:
            raise ElementNotFoundException("Content element not found for chapter: " + title)

        if not self.skip_conversion:
            self.apply_chapter_fix(chapter, soup, content_el, self.selectors.content_element)

            last_p_el = content_el.select_one(self.selectors.content_element + " > p:last-of-type")

            if not last_p_el:
                # In some cases (on Royal Road), the content is not directly inside the content_el, but wrapped in a single
                # div inside the content_el, so if a div exists we unwrap it and see what happens
                if "royalroad.com" in chapter.get("url", ""):
                    unwrap_toplevel_divs(soup, content_el, self.selectors.content_element)
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
            while last_p_el and last_p_el.find_next_sibling():
                last_p_el.find_next_sibling().decompose()

            # Remove empty elements if enabled
            if self.remove_empty_elements:
                for el in content_el.find_all(recursive=False):
                    if el.name != "hr" and el.get_text().strip() == "":
                        el.decompose()

            # Apply substitutions with CSS selector
            for s in [s for s in self.substitutions if s.selector_type == "css"]:
                if s.chapter_url and s.chapter_url != chapter.get("url"):
                    continue

                els = content_el.select(s.selector)

                if not len(els):
                    echo("Chapter '%s': No matches for selector '%s'. Please check if the config is up-to-date." % (title, s.selector))
                    continue

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
    def apply_chapter_fix(chapter, soup, content_el, content_el_selector):
        if func := CHAPTER_FIXES.get(chapter.get("url")):
            func(soup, content_el, content_el_selector)

    def convert_file(self, index, chapter):
        in_file = os.path.join(self.files.cache_folder, chapter.get("file"))
        out_file = os.path.join(self.files.book_folder, chapter.get("file"))

        if os.path.isfile(in_file):
            with open(in_file, "r", encoding="utf8") as file:
                doc = file.read()
            with open(out_file, "w", encoding="utf8") as file:
                doc = self.convert(doc, chapter)
                file.write(doc)
        else:
            raise FileNotFoundError("File %s not found" % in_file)

        return index

    def convert_all(self):
        with Pool(processes=cpu_count()) as pool:
            chapters_to_convert = filter(lambda t: not t[1].get("converted") and not t[1].get("url") in self.skip_urls, enumerate(self.manifest))
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
