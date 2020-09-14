from click import confirm, prompt, echo
from box import Box
from bs4 import BeautifulSoup
from requests import Session

from .crawler import Crawler
from ..exception import ElementNotFoundException


# noinspection DuplicatedCode
class WanderingInnPatreonCrawler(Crawler):
    def __init__(self, config: Box):
        super().__init__(config)
        self.session = Session()
        echo("Using WanderingInnPatreonCrawler")

    def download_chapter(self, url):
        r = self.session.get(url)

        soup = BeautifulSoup(r.content, "html.parser")

        title_el = soup.select_one(self.selectors.title_element)

        if not title_el:
            raise ElementNotFoundException("Title element not found")

        title = title_el.get_text().strip()
        title = title.replace(" ", " ")\
            .replace("  ", " ")\
            .replace("Protected: ", "")

        if soup.select_one(".post-password-form"):
            if confirm("Protected chapter %s reached! Do you have the password?" % title):
                password = prompt("Enter the password")

                self.session.post("https://wanderinginn.com/wp-pass.php", data={
                    'post_password': password,
                    'Submit': 'Enter'
                }, headers={
                    'referer': r.url
                })

                return self.download_chapter(r.url)
            else:
                return r.url, None, None, None

        return r.url, title, r.content, soup
