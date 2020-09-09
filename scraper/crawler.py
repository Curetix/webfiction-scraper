import os
import urllib.parse
import json

import requests
from box import Box
from bs4 import BeautifulSoup


class Crawler:
    def __init__(self, config: Box):
        self.start_url = config.start_url
        self.end_url = config.end_url
        self.selectors = config.selectors
        self.files = config.files
        self.manifest = []
        self.load_manifest()

        if len(self.manifest) > 0:
            self.start_url = self.manifest[len(self.manifest) - 1].get("url")

    def download(self, url=None):
        url = url if url else self.start_url
        index = len(self.manifest)

        r = requests.get(url)
        url = r.url  # In case of redirect, update our URL
        file_name = self.save_chapter(r.content, index)
        soup = BeautifulSoup(r.content, "html.parser")
        title_el = soup.select_one(self.selectors.title_element)
        print(title_el.get_text())
        manifest_entry = {
            "title": title_el.get_text(),
            "file": file_name,
            "converted": False,
            "url": url,
        }
        self.manifest.append(manifest_entry)
        self.save_manifest()

        if url == self.end_url:
            return True

        next_chapter_el = None

        if self.selectors.next_chapter_element_text:
            next_chapter_elements = soup.select(self.selectors.next_chapter_element)

            for el in next_chapter_elements:
                if el.get_text().strip() == self.selectors.next_chapter_element_text:
                    next_chapter_el = el
                    break
        else:
            next_chapter_el = soup.select_one(self.selectors.next_chapter_element)

        if next_chapter_el:
            next_url = next_chapter_el["href"]
            if not next_url.startswith("http"):
                # If URLs are relative, we add the scheme and hostname from the current url
                url_parsed = urllib.parse.urlparse(url)
                next_url = "%s://%s%s" % (
                    url_parsed.scheme,
                    url_parsed.hostname,
                    next_url if next_url.startswith("/") else "/%s" % next_url,
                )

            print(next_url)

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

    def load_manifest(self):
        if os.path.isfile(self.files.manifest_file):
            with open(os.path.join(self.files.manifest_file), "r") as file:
                self.manifest = json.load(file)
        else:
            return []

    def save_manifest(self):
        with open(os.path.join(self.files.manifest_file), "w") as file:
            json.dump(self.manifest, file, indent=2)

    def clean(self):
        self.manifest = []
        self.save_manifest()
        os.rmdir(self.files.cache_folder)
        os.mkdir(self.files.cache_folder)
