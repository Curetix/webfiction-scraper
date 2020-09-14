import os
import urllib.parse

from click import echo
from requests import get
from box import Box
from bs4 import BeautifulSoup

from ..manifest import Manifest
from ..exception import ElementNotFoundException


# noinspection DuplicatedCode
class Crawler:
    def __init__(self, config: Box):
        self.start_url = config.start_url
        self.end_url = config.end_url
        self.skip_chapters = config.skip_chapters
        self.selectors = config.selectors
        self.files = config.files
        self.manifest = Manifest(config.files.manifest_file)

    def start_download(self):
        if len(self.manifest) > 0:
            next_url = self.manifest[-1].get("url")
            index = len(self.manifest) - 1
        else:
            next_url = self.start_url
            index = 0

        while next_url is not None:
            url, title, content, soup = self.download_chapter(next_url)

            if not title and not content and not soup:
                return

            if url not in self.skip_chapters:
                file_name = self.save_chapter(content, index)
                self.add_chapter_to_manifest(index, url, title, file_name)
                echo("Downloaded chapter %s from %s" % (title, url))
            else:
                echo("Skipped chapter %s from %s" % (title, url))

            if url == self.end_url:
                return

            index += 1
            next_url = self.find_next_chapter_url(url, soup)

    def download_chapter(self, url):
        r = get(url)

        soup = BeautifulSoup(r.content, "lxml")

        title_el = soup.select_one(self.selectors.title_element)

        if not title_el:
            raise ElementNotFoundException("Title element not found")

        title = title_el.get_text().strip()
        title = title.replace(" ", " ")\
            .replace("  ", " ")

        return r.url, title, r.content, soup

    def save_chapter(self, content, index=0):
        chapter_file = "chapter%s%s%s.html" % (
            "0" if index < 100 else "",
            "0" if index < 10 else "",
            index,
        )
        with open(os.path.join(self.files.cache_folder, chapter_file), "wb") as file:
            file.write(content)
        return chapter_file

    def add_chapter_to_manifest(self, index, url, title, file_name):
        manifest_entry = {
            "title": title,
            "file": file_name,
            "converted": False,
            "url": url,
        }

        if len(self.manifest) - 1 == index:
            self.manifest[index] = manifest_entry
        else:
            self.manifest.append(manifest_entry)

        self.manifest.save()

    def find_next_chapter_url(self, current_url, soup):
        next_chapter_el = soup.select_one(self.selectors.next_chapter_element)

        if next_chapter_el:
            next_url = next_chapter_el.get("href")
            if not next_url.startswith("http"):
                # If URLs are relative, we add the scheme and hostname from the current url
                url_parsed = urllib.parse.urlparse(current_url)
                next_url = "%s://%s%s" % (
                    url_parsed.scheme,
                    url_parsed.hostname,
                    next_url if next_url.startswith("/") else "/%s" % next_url,
                )

            return next_url

        echo("Next chapter element not found")
        return None

    def clean(self):
        import shutil
        shutil.rmtree(self.files.cache_folder)
        os.mkdir(self.files.cache_folder)

        self.manifest.clear()
        self.manifest.save()
