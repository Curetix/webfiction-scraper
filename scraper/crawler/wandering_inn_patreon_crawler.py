from click import confirm, prompt, echo
from box import Box
from bs4 import BeautifulSoup
from requests import Session

from .crawler import Crawler
from ..exception import ElementNotFoundException


# noinspection DuplicatedCode
class WanderingInnPatreonCrawler(Crawler):
    def __init__(self, config: Box, patreon_cookie=None):
        super().__init__(config)
        echo("Using Wandering Inn Crawler")

        self.session = Session()
        self.session.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }

        self.attempted_patreon_password = False

        if patreon_cookie:
            self.patreon_session = Session()
            self.cookies = {"session_id": patreon_cookie}
        else:
            self.patreon_session = None

    def get_patreon_posts(self):
        if not self.patreon_session:
            echo("Patreon session not initialized! Please provide the cookie!")
            return

        payload = {
            "fields[post]": "content,published_at,patreon_url,post_type,title,url",
            "filter[campaign_id]": 568211,
            "sort": "-published_at"
        }

        r = self.patreon_session.get("https://www.patreon.com/api/posts", params=payload, cookies=self.cookies)

        if r:
            return r.json().get("data")

    def get_patreon_password(self, chapter_title, chapter_url):
        echo("Trying to automatically find password on Patreon...")

        posts = self.get_patreon_posts()

        if not posts:
            return

        found_post = None

        post_by_title = list(filter(lambda p: p["attributes"].get("title", "").strip() == chapter_title, posts))

        if len(post_by_title) > 0:
            found_post = post_by_title[0]
        else:
            post_by_url = list(filter(lambda p: chapter_url.replace("https://", "") in p["attributes"].get("content", ""), posts))

            if len(post_by_url) > 0:
                found_post = post_by_url[0]

        if not found_post:
            return

        soup = BeautifulSoup(found_post["attributes"]["content"], "lxml")
        password_element = soup.select_one("p:-soup-contains(\"Password:\")")

        if password_element:
            echo("Found a password! But does it work?")
            return password_element.find_next_sibling().get_text().strip()

    def download_chapter(self, url):
        r = self.session.get(url)

        if r.status_code != 200:
            echo("Something went wrong! URL: %s, Status: %s" % (r.url, r.status_code))
            if confirm("Do you want to enter another URL?"):
                new_url = prompt("Enter the URL")
                return self.download_chapter(new_url)
            else:
                return r.url, None, None, None

        soup = BeautifulSoup(r.content, "html.parser")

        title_el = soup.select_one(self.selectors.title_element)

        if not title_el:
            raise ElementNotFoundException("Title element not found")

        title = title_el.get_text().strip()
        title = title.replace(" ", " ")\
            .replace("  ", " ")\
            .replace("Protected: ", "")\
            .replace("Patron Early Access: ","")

        password_form = soup.select_one(".entry-content form[method=post]")
        if password_form:
            echo("Protected chapter %s reached!" % title)

            password = None

            # This doesn't work anymore because of Cloudflare protection, I'll disable it for now. Maybe permanently.
            # if self.patreon_session and not self.attempted_patreon_password:
            #     self.attempted_patreon_password = True
            #     password = self.get_patreon_password(title, url)

            if not password:
                if confirm("Do you have the latest Patreon password for this chapter?", default=True):
                    password = prompt("Enter the password")
                else:
                    return r.url, None, None, None

            self.session.post(password_form.get("action") or "https://wanderinginn.com/wp-login.php?action=postpass", data={
                'post_password': password,
                'Submit': 'Submit'
            }, headers={
                'referer': r.url
            })

            return self.download_chapter(r.url)

        return r.url, title, r.content, soup

    def find_next_chapter_url(self, current_url, soup):
        # The Volume 7 "Finale" is split into multiple chapters, but the following chapters are linked at end of 
        # the content element, instead of the usual "Next Chapter" element, so we're just doing this manually here.
        if current_url == "https://wanderinginn.com/2020/12/23/solstice-pt-3/":
            return "https://wanderinginn.com/2020/12/23/solstice-pt-4/"
        elif current_url == "https://wanderinginn.com/2020/12/23/solstice-pt-4/":
            return "https://wanderinginn.com/2020/12/23/solstice-pt-5/"
        elif current_url == "https://wanderinginn.com/2020/12/23/solstice-pt-5/":
            return "https://wanderinginn.com/2020/12/23/solstice-pt-6/"
        elif current_url == "https://wanderinginn.com/2020/12/23/solstice-pt-6/":
            return "https://wanderinginn.com/2020/12/23/solstice-pt-7/"
        elif current_url == "https://wanderinginn.com/2020/12/23/solstice-pt-7/":
            return "https://wanderinginn.com/2020/12/23/solstice-pt-8/"
        elif current_url == "https://wanderinginn.com/2020/12/23/solstice-pt-8/":
            return "https://wanderinginn.com/2020/12/23/solstice-pt-9/"
        else:
            return super(WanderingInnPatreonCrawler, self).find_next_chapter_url(current_url, soup)
