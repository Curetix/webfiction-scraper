import os
import urllib.parse
import json

import requests
from bs4 import BeautifulSoup

from scraper.binder import Binder
from scraper.converter import Converter


class Crawler:
    def __init__(self, config):
        self.start_url = config.get("startUrl")
        self.end_url = config.get("endUrl")
        self.files = config.get("files")
        cache_folder = self.files.get("cacheFolder")
        self.cache_path = (
            cache_folder
            if os.path.isabs(cache_folder)
            else os.path.join(self.files.get("workingFolder"), cache_folder)
        )
        self.selectors = config.get("selectors")
        self.converter = Converter(config)
        self.binder = Binder(config)
        self.manifest = self.load_manifest()

    def download(self, url, index=0, convert_after_dl=True):
        r = requests.get(url)
        file_name = self.save_chapter(r.content, index)
        soup = BeautifulSoup(r.content, "html.parser")
        title_el = soup.select_one(self.selectors.get("titleElement"))
        print(title_el.get_text())
        manifest_entry = {
            "title": title_el.get_text(),
            "file": file_name,
            "converted": False,
            "url": url,
        }
        if index < len(self.manifest):
            self.manifest[index] = manifest_entry
        else:
            self.manifest.append(manifest_entry)
        self.save_manifest(self.manifest)

        if url == self.end_url:
            return True

        next_chapter_el = soup.select_one(self.selectors.get("nextChapterElement"))

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
            return self.download(next_url, index + 1)
        else:
            return True

    def save_chapter(self, content, index=0):
        chapter_file = "chapter%s%s%s.html" % (
            "0" if index < 100 else "",
            "0" if index < 10 else "",
            index,
        )
        chapter_path = os.path.join(self.cache_path, chapter_file)
        with open(chapter_path, "wb") as file:
            file.write(content)
        return chapter_file

    def load_manifest(self):
        if os.path.isfile(
            os.path.join(self.files.get("workingFolder"), "manifest.json")
        ):
            with open(
                os.path.join(self.files.get("workingFolder"), "manifest.json"), "r"
            ) as file:
                return json.load(file)
        else:
            return []

    def save_manifest(self, manifest):
        with open(
            os.path.join(self.files.get("workingFolder"), "manifest.json"), "w"
        ) as file:
            json.dump(manifest, file, indent=2),

    def run(
        self,
        download=True,
        download_new=False,
        convert=True,
        convert_new=False,
        bind=True,
    ):
        if download:
            if download_new or len(self.manifest) == 0:
                self.manifest = []
                self.save_manifest(self.manifest)
                os.rmdir(self.cache_path)
                os.mkdir(self.cache_path)
                download_result = self.download(
                    self.start_url, convert_after_dl=convert
                )
            else:
                index = len(self.manifest) - 1
                download_result = self.download(
                    self.manifest[index].get("url"), index, convert
                )
