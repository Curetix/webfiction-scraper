import json
import os
import sys
import urllib.parse
import uuid

import click
import yaml
from box import Box
from click import echo
from schema import Schema, SchemaError

from scraper.const import CONFIG_SCHEMA
from scraper.converter import Converter
from scraper.crawler import Crawler
from scraper.utils import normalize_string, lowercase_clean
from scraper.generator import RoyalRoadConfigGenerator

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_FOLDER = os.path.dirname(SCRIPT_PATH)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("config")
@click.option("--clean-download", is_flag=True)
@click.option("--clean-convert", is_flag=True)
def run(config, clean_download, clean_convert):
    """Run the scraper with the provided CONFIG.

    CONFIG can be a path to a valid JSON or YAML config file,
    or the name of a built-in config. To list all available
    default configs, use the command LIST-CONFIGS.
    """
    config_name = config

    if config_name in get_builtin_configs():
        path = os.path.join(SCRIPT_FOLDER, "configs", "%s.yaml" % config_name)
    else:
        path = config_name

    if not os.path.isfile(path):
        echo("Couldn't find config file!")
        sys.exit(1)

    if path.endswith(".json"):
        with open(path, "r") as file:
            config = json.load(file)
    elif path.endswith(".yaml") or path.endswith(".yml"):
        with open(path, "r") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
    else:
        echo("Invalid file extension, only .json and .yaml/.yml are supported!")
        return

    config = get_validated_config(config_name, config)

    crawler = Crawler(config)
    if clean_download:
        crawler.clean()
    crawler.download()

    converter = Converter(config)
    if clean_convert:
        converter.clean()
    converter.convert_all()

    # import code
    # variables = variables = {**globals(), **locals()}
    # shell = code.InteractiveConsole(variables)
    # shell.interact()


@cli.command()
def list_configs():
    """List all available built-in configs."""
    echo("Available built-in configs:")
    for c in get_builtin_configs():
        echo(c)


@cli.command()
@click.argument("url")
@click.option("--name", type=str)
def generate_config(url, name):
    if not url.startswith("http"):
        url = "https://" + url

    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc

    if domain == "royalroad.com" or domain == "www.royalroad.com":
        echo("Detected Royal Road URL!")
        generator = RoyalRoadConfigGenerator(url)
    else:
        echo("Invalid URL or site not supported!")
        return

    config = generator.get_config()
    if not name:
        name = config.metadata.title

    try:
        Schema(CONFIG_SCHEMA).validate(config)
    except SchemaError as e:
        echo(e)
        if not click.confirm("Couldn't validate newly generated config, save anyways?"):
            return

    config.to_yaml(filename="configs/%s.yaml" % name)

    echo("Config for \"%s\" successfully generated, validated and saved!" % config.metadata.title)
    echo("It can now be used with \"client.py run %s\"!" % name)


def get_validated_config(config_name: str, config: Box):
    try:
        validated = Schema(CONFIG_SCHEMA).validate(config)
    except SchemaError as e:
        echo(e)
        sys.exit(1)

    validated = Box(validated, camel_killer_box=True)
    files = validated.files
    metadata = validated.metadata
    title = normalize_string(metadata.title)

    if not metadata.get("identifier"):
        ident_string = "%s-%s" % (
            lowercase_clean(metadata.get("author")),
            lowercase_clean(metadata.get("title")),
        )
        validated.metadata.identifier = str(uuid.uuid5(
            uuid.NAMESPACE_DNS, ident_string
        ))

    working_folder = files.get("working_folder")

    if not working_folder:
        working_folder = os.path.join(SCRIPT_FOLDER, "data", os.path.basename(config_name))
    elif working_folder and not os.path.isabs(working_folder):
        working_folder = os.path.join(SCRIPT_FOLDER, "data", working_folder)

    cache_folder = os.path.join(working_folder, "cache")
    book_folder = os.path.join(working_folder, "book")
    manifest_file = os.path.join(working_folder, "manifest.json")

    epub_file = files.get("epub_file")
    cover_file = files.get("cover_file")

    if not epub_file:
        epub_file = os.path.join(working_folder, title + ".epub")
    elif epub_file and not os.path.isabs(epub_file):
        epub_file = os.path.join(working_folder, epub_file)

    # TODO: if file is a URL, download it. If it isn't specified, generate one.
    if not cover_file:
        cover_file = os.path.join(working_folder, "cover.jpg")
    elif cover_file and not os.path.isabs(cover_file):
        cover_file = os.path.join(working_folder, cover_file)

    validated.files = Box(
        working_folder=working_folder,
        cache_folder=cache_folder,
        book_folder=book_folder,
        epub_file=epub_file,
        cover_file=cover_file,
        manifest_file=manifest_file
    )

    if not os.path.isdir(working_folder):
        os.mkdir(working_folder)

    if not os.path.isdir(cache_folder):
        os.mkdir(cache_folder)

    if not os.path.isdir(book_folder):
        os.mkdir(book_folder)

    return validated


def get_builtin_configs():
    configs = []
    for file in os.listdir(os.path.join(SCRIPT_FOLDER, "configs")):
        if file.endswith(".json") or file.endswith(".yaml"):
            configs.append(file.replace(".json", "").replace(".yaml", ""))
    return configs


if __name__ == "__main__":
    cli()
