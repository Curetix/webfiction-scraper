from time import sleep

import click
import questionary
from questionary import Choice
from box import Box
from bs4 import BeautifulSoup
from click import echo, progressbar
from requests import get

from scraper import FictionScraperClient
from scraper.utils import list_fiction_configs

client = FictionScraperClient()


@click.group()
def cli():
    pass


@cli.command()
def interactive():
    """Start the scraper interactively."""
    configs = list_fiction_configs() + list_fiction_configs(user_dir=True)
    config_choices = []
    with progressbar(configs, label="Loading configs") as bar:
        for config_name in bar:
            config = client.load_fiction_config(config_name)
            config_choices.append(Choice(title=config.metadata.title, value=config_name))
    config_choices.sort(key=lambda c: c.title)

    answers = questionary.form(
        config_name=questionary.select(
            "Which config do you want to run?",
            choices=config_choices
        ),
        tasks=questionary.checkbox(
            "Which tasks do you want to run?",
            choices=[
                Choice(title="Download chapters", value="download", checked=True),
                Choice(title="Clean download chapters", value="clean_download", checked=False),
                Choice(title="Convert chapters", value="convert", checked=True),
                Choice(title="Clean convert chapters", value="clean_convert", checked=False),
                Choice(title="Bind chapters into eBook", value="bind", checked=True),
                Choice(title="Create eBook formats specified in the config", value="format", checked=False)
            ]
        )
    ).ask()

    if not answers:
        return

    config_name = answers.get("config_name")
    tasks = answers.get("tasks")

    if not tasks:
        return

    client.run(
        config_name,
        "download" in tasks,
        "clean_download" in tasks,
        "convert" in tasks,
        "clean_convert" in tasks,
        "bind" in tasks,
        "format" in tasks
    )

    input("Press any key to exit...")


@cli.command()
@click.argument("config_name")
@click.option("--download/--no-download", default=True, help="Enable/disable chapter download")
@click.option("--clean-download", is_flag=True, help="Clear existing downloaded chapters")
@click.option("--convert/--no-convert", default=True, help="Enable/disable chapter conversion")
@click.option("--clean-convert", is_flag=True, help="Clear existing converted chapters")
@click.option("--bind/--no-bind", default=True, help="Enable/disable eBook creation")
@click.option("--ebook-convert/--no-ebook-convert", default=True, help="Create eBook formats specified in the config")
def run(config_name, download, clean_download, convert, clean_convert, bind, ebook_convert):
    """Run the scraper with the provided CONFIG_NAME.

    CONFIG_NAME can be a path to a YAML config file, the name of a built-in config or the name of a config inside
    the users configs/ directory. To list all automatically detected config files, use the list-configs command.
    """
    client.run(config_name, download, clean_download, convert, clean_convert, bind, ebook_convert)


@cli.command()
def monitor():
    """Monitor feeds and run the scraper when content is posted."""
    last_posts = Box()
    monitored_fictions = client.client_config.get("monitored_fictions")

    if not monitored_fictions:
        echo("No fictions to monitor configured!")
        return

    while True:
        for fiction in monitored_fictions:
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
def list_configs():
    """List all detected configs."""
    echo("Available built-in configs:")
    for c in list_fiction_configs() + list_fiction_configs(user_dir=True):
        echo(c)


@cli.command()
@click.argument("url")
@click.option("--name", type=str, help="Name of the config (file)")
def generate_config(url, name=None):
    """Generate a config file for a fiction from a support site.

    URL can be either the fictions overview page or a chapter (which will be used as the startUrl config entry).

    Currently supported sites:

    - Royal Road
    """
    config_name = client.generate_fiction_config(url, name)
    # echo("Config can now be used with \"webfictionscraper.py run %s\"!" % config_name)
    if questionary.confirm("Do you want to run the config now?", default=False).ask():
        client.run(config_name, True, False, True, False, True, False)


if __name__ == "__main__":
    cli()
