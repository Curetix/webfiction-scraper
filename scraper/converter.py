import os

from bs4 import BeautifulSoup

from scraper.manifest import Manifest


class Converter:
    def __init__(self, config):
        self.files = config.files
        self.selectors = config.selectors
        self.substitutions = config.substitutions
        self.remove_empty_elements = config.remove_empty_elements
        self.manifest = Manifest(config.files.manifest_file)

    def convert(self, html, url):
        return self.convert_soup(BeautifulSoup(html, "lxml"), url)

    def convert_soup(self, soup, url):
        # TODO: create base HTML doc, set content_el as body

        content_el = soup.select_one(self.selectors.get("contentElement"))

        if not content_el:
            # TODO: raise error
            pass

        last_p_el = content_el.select_one("p:last-of-type")

        while content_el.contents[len(content_el.contents) - 1] != last_p_el:
            content_el.contents[len(content_el.contents) - 1].decompose()

        for el in content_el.contents:
            if self.remove_empty_elements and el.get_text().strip() == "":
                # TODO: modifying the tree while in the loop probably'll cause problems
                el.decompose()
                continue

            if el.get("dir") == "ltr":
                del el["dir"]

            del el["align"]

            if el.get("style") == "text-align:left;":
                del el["style"]

        for s in self.substitutions:
            if s.get("chapterUrl") and s.get("chapterUrl") != url:
                continue

            if s.get("css"):
                els = content_el.select(s.get("css"))
                for el in els:
                    pass

        return content_el

    def convert_file(self, path, converted_path, url):
        if os.path.isfile(path):
            with open(path, "rb") as file:
                content = file.read()
            with open(converted_path, "w+") as file:
                file.write(str(self.convert(content, url)))
        else:
            raise FileNotFoundError()

    def convert_all(self):
        for (i, f) in enumerate(self.manifest):
            if not f.get("converted"):
                self.convert_file(
                    os.path.join(self.files.cache_folder, f.get("file")),
                    os.path.join(self.files.book_folder, f.get("file")),
                    f.get("url")
                )
                self.manifest[i].update({"converted": True})

    def clean(self):
        import shutil
        shutil.rmtree(self.files.book_folder)
        os.mkdir(self.files.book_folder)

        for (i, e) in self.manifest:
            self.manifest[i].update({"converted": False})
