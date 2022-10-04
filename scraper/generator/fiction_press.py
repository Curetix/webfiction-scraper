import re

from requests import get
from box import Box
from bs4 import BeautifulSoup

from .generator import ConfigGenerator
from ..exception import ElementNotFoundException, InvalidPageException

CHAPTER_PATTERN = re.compile(r"(?:http[s]://)?www\.fictionpress\.com/s/\d+/\d+/.+")


class FictionPressGenerator(ConfigGenerator):
    def __init__(self, start_url, end_url=None):
        super().__init__(start_url, end_url)

    def get_selectors(self):
        return Box(
            titleElement="select#chap_select option[selected]",
            contentElement="#storytext",
            nextChapterElement="button.btn:-soup-contains(\"Next\")"
        )

    def get_metadata(self):
        start_url = self.config.startUrl

        r = get(start_url)
        soup = BeautifulSoup(r.content, "html.parser")

        if not re.match(CHAPTER_PATTERN, start_url):
            raise InvalidPageException()

        self.config.files = Box(coverFile=soup.select_one("#img_large img").get("src"))
        self.config.startUrl = start_url
        metadata = Box(
            title=soup.select_one("#profile_top b.xcontrast_txt").get_text(),
            author=soup.select_one("#profile_top a.xcontrast_txt").get_text(),
            description=soup.select_one("#profile_top div.xcontrast_txt").get_text()
        )

        return metadata
