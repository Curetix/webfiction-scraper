import os
from time import sleep

from click import echo
from requests import get
from bs4 import BeautifulSoup
from box import Box

from scraper import FictionScraperClient

SCRIPT_FOLDER = os.path.dirname(os.path.realpath(__file__))


def run():
    client_config = Box()
    configs_folder = os.path.join(SCRIPT_FOLDER, "configs")
    data_folder = os.path.join(SCRIPT_FOLDER, "data")

    if os.path.isfile(path := os.path.join(SCRIPT_FOLDER, "client.yaml")):
        client_config = Box.from_yaml(filename=path)
        if folder := client_config.get("dataFolder"):
            data_folder = folder

    client = FictionScraperClient(client_config, configs_folder, data_folder)

    monitor_config = Box.from_yaml(filename=os.path.join(SCRIPT_FOLDER, "monitor.yaml"), camel_killer_box=True)
    last_posts = Box()

    while True:
        for fiction in monitor_config.monitored_fictions:
            c = fiction.config_name
            r = get(fiction.rss_feed_url)
            soup = BeautifulSoup(r.content, "lxml")
            latest_post = soup.find("item").find("link").get_text()

            if last_posts.get(c) != latest_post:
                last_posts[c] = latest_post

                if not last_posts.get(c):
                    echo("Initial post recorded for: %s" % c)
                    continue

                echo("New post for: %s" % c)

                options = fiction.get("client_options", Box())

                client.run(
                    c,
                    options.get("download", True),
                    options.get("clean_download", False),
                    options.get("convert", True),
                    options.get("clean_convert", False),
                    options.get("bind", True),
                    options.get("ebook_convert", True)
                )
            else:
                echo("Nothing new for:  %s" % c)

        echo("Done! Sleeping...")
        sleep(1800)


if __name__ == "__main__":
    run()
