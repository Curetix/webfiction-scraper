import os
from time import sleep

import click
from PyInquirer import prompt
from box import Box
from bs4 import BeautifulSoup
from click import echo
from requests import get

from scraper import FictionScraperClient

SCRIPT_FOLDER = os.path.dirname(os.path.realpath(__file__))


@click.group()
def cli():
    pass


@cli.command()
def interactive():
    """Start an interactive session."""
    questions = [
        {
            "type": "list",
            "message": "Which config do you want to run?",
            "name": "config_name",
            "choices": [{"name": f} for f in client.get_fiction_configs()]
        },
        {
            "type": "checkbox",
            "message": "Which tasks do you want to run?",
            "name": "tasks",
            "choices": [
                {
                    "name": "Download chapters",
                    "checked": True
                },
                {
                    "name": "Clean download chapters",
                    "checked": False
                },
                {
                    "name": "Convert chapters",
                    "checked": True
                },
                {
                    "name": "Clean convert chapters",
                    "checked": False
                },
                {
                    "name": "Bind chapters into eBook",
                    "checked": True
                },
                {
                    "name": "Create eBook formats specified in the config",
                    "checked": True
                }
            ]
        },
    ]

    answers = prompt(questions)

    if not answers:
        return

    config_name = answers.get("config_name")
    tasks = answers.get("tasks")

    if not tasks:
        return

    client.run(
        config_name,
        "Download chapters" in tasks,
        "Clean download chapters" in tasks,
        "Convert chapters" in tasks,
        "Clean convert chapters" in tasks,
        "Bind chapters into eBook" in tasks,
        "Create eBook formats specified in the config" in tasks
    )


@cli.command()
@click.argument("config")
@click.option("--download/--no-download", default=True, help="Enable/disable chapter download")
@click.option("--clean-download", is_flag=True, help="Clear existing downloaded chapters")
@click.option("--convert/--no-convert", default=True, help="Enable/disable chapter conversion")
@click.option("--clean-convert", is_flag=True, help="Clear existing converted chapters")
@click.option("--bind/--no-bind", default=True, help="Enable/disable eBook creation")
@click.option("--ebook-convert/--no-ebook-convert", default=True, help="Create eBook formats specified in the config")
def run(config, download, clean_download, convert, clean_convert, bind, ebook_convert):
    """Run the scraper with the provided CONFIG.

    CONFIG can be a path to a valid JSON or YAML config file,
    or the name of a file inside the configs/ folder.
    """
    client.run(config, download, clean_download, convert, clean_convert, bind, ebook_convert)


@cli.command()
def monitor():
    last_posts = Box()

    if not client_config.get("monitored_fictions"):
        echo("No fictions to monitor configured!")
        return

    while True:
        for fiction in client_config.monitored_fictions:
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


@cli.command()
@click.option("--info", is_flag=True, help="Load the configs and list more information")
def list_configs():
    """List all configs inside the configs/ folder."""
    echo("Available built-in configs:")
    for c in client.get_fiction_configs():
        echo(c)


@cli.command()
@click.argument("url")
@click.option("--name", type=str, help="Name of the config (file)")
def generate_config(url, name):
    """Generate a config file for a fiction from a support site.

    URL can be either the fictions overview page or a chapter (which will be used as the startUrl config entry).

    Currently supported sites:
    - Royal Road
    """
    client.generate_fiction_config(url, name)


if __name__ == "__main__":
    client_config = Box()
    configs_folder = os.path.join(SCRIPT_FOLDER, "configs")
    data_folder = os.path.join(SCRIPT_FOLDER, "data")

    if os.path.isfile(path := os.path.join(SCRIPT_FOLDER, "client.yaml")):
        client_config = Box.from_yaml(filename=path)
        if folder := client_config.get("dataFolder"):
            data_folder = folder

    client = FictionScraperClient(client_config, configs_folder, data_folder)
    cli()
