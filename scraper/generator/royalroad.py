import urllib.parse
import re

from requests import get
from box import Box
from bs4 import BeautifulSoup

from scraper.generator.generator import ConfigGenerator
b
FICTION_PAGE_PATTERN = re.compile(r"(?:http[s]://)?www\.royalroad\.com/fiction/\d+/.+")
CHAPTER_PATTERN = re.compile(r"(?:http[s]://)?www\.royalroad\.com/fiction/\d+/.+/chapter/\d+/.+")


class RoyalRoadConfigGenerator(ConfigGenerator):
    def __init__(self, start_url, end_url=None):
        super().__init__(start_url, end_url)

    def get_selectors(self):
        return Box(
            title_element="h1",
            content_element=".chapter-content",
            next_chapter_element=".nav-buttons .col-lg-offset-6 a"
        )

    def get_metadata(self):
        start_url = self.config.start_url
        fiction_url = None

        r = get(start_url)
        soup = BeautifulSoup(r.content, "html.parser")

        fiction_page_match = re.match(FICTION_PAGE_PATTERN, start_url)
        chapter_page_match = re.match(CHAPTER_PATTERN, start_url)

        if fiction_page_match and not chapter_page_match:
            fiction_url = start_url
            # TODO: get URL of first chapter
        elif chapter_page_match:
            # TODO: get URL of fiction page
            pass
