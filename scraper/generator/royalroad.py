import re

from requests import get
from box import Box
from bs4 import BeautifulSoup

from .generator import ConfigGenerator
from ..exception import ElementNotFoundException, InvalidPageException

FICTION_PAGE_PATTERN = re.compile(r"(?:http[s]://)?www\.royalroad\.com/fiction/\d+/.+")
CHAPTER_PATTERN = re.compile(r"(?:http[s]://)?www\.royalroad\.com/fiction/\d+/.+/chapter/\d+/.+")


class RoyalRoadConfigGenerator(ConfigGenerator):
    def __init__(self, start_url, end_url=None):
        super().__init__(start_url, end_url)

    def get_selectors(self):
        return Box(
            titleElement=".fic-header h1",
            contentElement=".chapter-content",
            nextChapterElement=".nav-buttons a:-soup-contains(\"Next Chapter\")"
        )

    def get_metadata(self):
        start_url = self.config.startUrl

        r = get(start_url)
        soup = BeautifulSoup(r.content, "html.parser")

        btn = soup.select_one(".fic-buttons a.btn-primary")

        if not btn:
            raise ElementNotFoundException("Fiction / chapter button not found")

        fiction_page_match = re.match(FICTION_PAGE_PATTERN, start_url)
        chapter_page_match = re.match(CHAPTER_PATTERN, start_url)

        if fiction_page_match and not chapter_page_match:
            start_url = "https://www.royalroad.com" + btn.get("href")
        elif chapter_page_match:
            r = get("https://www.royalroad.com" + btn.get("href"))
            soup = BeautifulSoup(r.content, "html.parser")
        else:
            raise InvalidPageException()

        self.config.files = Box(coverFile=soup.select_one(".fic-header img").get("src"))
        self.config.startUrl = start_url
        metadata = Box(
            title=soup.select_one(".fic-header h1").get_text(),
            author=soup.select_one(".fic-header h4 a").get_text(),
            description=soup.select_one(".description .hidden-content").get_text()
        )

        return metadata
