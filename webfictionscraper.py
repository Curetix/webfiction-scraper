import os

import click
import questionary
from questionary import Choice, Separator
from click import echo, progressbar

from scraper import FictionScraperClient

client = FictionScraperClient()

HEADLESS = False


@click.group()
@click.option("--headless", is_flag=True, help="Do not prompt for any user input")
def cli(headless):
    if headless or os.environ.get("SCRAPER_HEADLESS") == "true":
        global HEADLESS
        HEADLESS = True


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start the scraper interactively."""
    if HEADLESS:
        echo("The interactive CLI is not available because headless mode is active.")
        echo("Don't pass the --headless argument and set the SCRAPER_HEADLESS env variable to anything but 'true'.")
        return

    configs = client.list_fiction_configs()
    choices = []

    if len(configs) > 0:
        with progressbar(configs, label="Loading configs") as bar:
            for config_name in bar:
                try:
                    config = client.load_fiction_config(config_name)
                except Exception as error:
                    echo('Error loading config \'%s\': %s' % (config_name, error))
                    input('Press enter to continue...')
                    continue

                if config:
                    choices.append(Choice(title=config.metadata.title, value='config:%s' % config_name))
                else:
                    input('Press enter to continue...')

        choices.sort(key=lambda c: c.title)
    else:
        choices.append(Choice("None", disabled="No configs found"))

    choices = [
        Choice(title="Download config(s)", value="download"),
        Choice(title="Generate new config", value="generate"),
        Separator()
    ] + choices

    click.clear()
    selected = questionary.select(
        "What do you want to do or which config do you want to run?",
        choices=choices
    ).ask()

    if not selected:
        return

    if selected == "download":
        configs = client.list_fiction_configs(remote=True)
        choices = [
            Choice("All (%s) configs" % len(configs), value="all"),
            Separator()
        ] + [Choice(c, value="config:%s" % c) for c in configs]

        configs_to_download = questionary.checkbox(
            "Which configs do you want to download?",
            choices=choices,
        ).ask()

        if not configs_to_download:
            return
        if "all" in configs_to_download:
            ctx.invoke(download_config, all=True)
        else:
            configs_to_download = [c.replace("config:", "") for c in configs_to_download]

            with progressbar(configs_to_download, label="Downloading configs") as bar:
                for c in bar:
                    ctx.invoke(download_config, config_name=c, prompt=False)
    elif selected == "generate":
        answers = questionary.form(
            url=questionary.text("What's the URL of the web fiction or the first chapter?"),
            name=questionary.text("What do you want to name the config? (Optional, press Enter for default)")
        ).ask()
        if not answers:
            return
        ctx.invoke(generate_config, url=answers.get("url"), name=answers.get("name"))
    elif selected.startswith("config:"):
        config_name = selected.replace("config:", "")

        tasks = questionary.checkbox(
            "Which tasks do you want to run?",
            choices=[
                Choice(title="Download chapters", value="download", checked=True),
                Choice(title="Clean download chapters", value="clean_download", checked=False),
                Choice(title="Convert chapters", value="convert", checked=True),
                Choice(title="Clean convert chapters", value="clean_convert", checked=False),
                Choice(title="Bind chapters into eBook", value="bind", checked=True),
                Choice(title="Create eBook formats specified in the config", value="format", checked=False)
            ]
        ).ask()

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

    if questionary.confirm("Do you want to return to the main menu?").ask():
        click.clear()
        ctx.invoke(interactive)


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
@click.option("--remote", "-r", is_flag=True, help="List all configs in the remote repository")
def list_configs(remote: bool):
    """List all detected configs."""
    configs = client.list_fiction_configs(remote)

    if remote and not configs:
        echo("Could not get repository contents.")
    elif len(configs) == 0:
        echo("No configs available.")
    else:
        echo("Available configs:")
        for c in configs:
            echo("  %s" % c)


@cli.command()
@click.argument("config_name", required=False)
@click.option("--all", "-a", is_flag=True, help="Download all available remote configs")
@click.option("--overwrite", "-o", is_flag=True, help="Overwrite configs when they already exist")
def download_config(config_name: str, all: bool, overwrite: bool, prompt=True):
    """Download a config from the remote repository."""
    if not config_name and not all:
        echo("Either the config_name argument or the --all option is required.")
        return

    if all:
        configs = client.list_fiction_configs(remote=True)
        downloaded = []
        with progressbar(configs, label="Downloading configs") as bar:
            for c in bar:
                success = client.download_fiction_config(c, overwrite)
                if not success:
                    echo("Downloading config %s was not successful." % c)
                else:
                    downloaded.append(c)

        echo("Downloaded %s configs!" % len(downloaded))
    else:
        success = client.download_fiction_config(config_name, overwrite)
        if not success:
            echo("Download was not successful.")
            return

        echo("Config %s was downloaded!" % config_name)

        if not HEADLESS and prompt and questionary.confirm("Do you want to run the config now?", default=False).ask():
            client.run(config_name, True, False, True, False, True, False)


@cli.command()
@click.argument("url")
@click.option("--name", "-n", type=str, help="Name of the config (file)")
def generate_config(url, name=None):
    """Generate a config file for a fiction from a support site.

    URL can be either the fictions overview page or a chapter (which will be used as the startUrl config entry).

    Currently supported sites:

    - Royal Road
    - FictionPress
    """
    config_name = client.generate_fiction_config(url, name)
    if not HEADLESS and questionary.confirm("Do you want to run the config now?", default=False).ask():
        client.run(config_name, True, False, True, False, True, False)


if __name__ == "__main__":
    cli()
