import os
import urllib.parse

from click import echo
from requests import get
from box import Box
from bs4 import BeautifulSoup

from scraper.generator import ElementNotFoundException
from scraper.manifest import Manifest


class Crawler:
    def __init__(self, config: Box):
        self.start_url = config.start_url
        self.end_url = config.end_url
        self.skip_chapters = config.skip_chapters
        self.selectors = config.selectors
        self.files = config.files
        self.manifest = Manifest(config.files.manifest_file)

        self.continue_from_url = None
        if len(self.manifest) > 0:
            self.continue_from_url = self.manifest[-1].get("url")

    def download(self, url=None):
        url = url if url else self.continue_from_url if self.continue_from_url else self.start_url
        index = len(self.manifest)

        r = get(url)
        url = r.url  # In case of redirect, update our URL

        if len(self.manifest) > 0 and url == self.manifest[-1].get("url"):
            index = len(self.manifest) - 1

        soup = BeautifulSoup(r.content, "html.parser")
        title_el = soup.select_one(self.selectors.title_element)

        if not title_el:
            raise ElementNotFoundException("Title element not found on " + url)

        title = title_el.get_text().strip()
        title = title.replace(" ", " ").replace("  ", " ")  # Replace unicode spaces and double spaces

        if url not in self.skip_chapters:
            file_name = self.save_chapter(r.content, index)
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

            echo("Downloaded chapter %s from %s" % (title, url))
        else:
            echo("Skipped chapter %s from %s" % (title, url))

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
            echo("Next chapter element not found")
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
        self.manifest.save()
        self.continue_from_url = None
