import os
import urllib.parse

from requests import get
from box import Box
from bs4 import BeautifulSoup

from scraper.manifest import Manifest


class Crawler:
    def __init__(self, config: Box):
        self.start_url = config.start_url
        self.end_url = config.end_url
        self.selectors = config.selectors
        self.files = config.files
        self.manifest = Manifest(config.files.manifest_file)

        if len(self.manifest) > 0:
            self.start_url = self.manifest[len(self.manifest) - 1].get("url")

    def download(self, url=None):
        url = url if url else self.start_url
        index = len(self.manifest)

        r = get(url)
        url = r.url  # In case of redirect, update our URL
        file_name = self.save_chapter(r.content, index)
        soup = BeautifulSoup(r.content, "html.parser")
        title_el = soup.select_one(self.selectors.title_element)
        print("Current chapter: " + title_el.get_text())
        print("Current URL: " + url)
        manifest_entry = {
            "title": title_el.get_text(),
            "file": file_name,
            "converted": False,
            "url": url,
        }
        self.manifest.append(manifest_entry, True)

        if url == self.end_url:
            return True

        next_chapter_el = soup.select_one(self.selectors.next_chapter_element)

        if next_chapter_el:
            next_url = next_chapter_el.get("href")
            if not next_url.startswith("http"):
                # If URLs are relative, we add the scheme and hostname from the current url
                url_parsed = urllib.parse.urlparse(url)
                next_url = "%s://%s%s" % (
                    url_parsed.scheme,
                    url_parsed.hostname,
                    next_url if next_url.startswith("/") else "/%s" % next_url,
                )

            return self.download(next_url)
        else:
            print("next_chapter_el not found")
            return True

    def save_chapter(self, content, index=0):
        chapter_file = "chapter%s%s%s.html" % (
            "0" if index < 100 else "",
            "0" if index < 10 else "",
            index,
        )
        with open(os.path.join(self.files.cache_folder, chapter_file), "wb") as file:
            file.write(content)
        return chapter_file

    def clean(self):
        import shutil
        shutil.rmtree(self.files.cache_folder)
        os.mkdir(self.files.cache_folder)

        self.manifest.clear()
