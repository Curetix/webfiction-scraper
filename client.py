import json
import os
import sys
import urllib.parse
import uuid

import click
import yaml
from PyInquirer import prompt
from box import Box
from click import echo
from schema import Schema, SchemaError

from scraper import Crawler, Converter, Binder
from scraper import RoyalRoadConfigGenerator, WanderingInnPatreonCrawler
from scraper.const import CONFIG_SCHEMA
from scraper.utils import normalize_string, lowercase_clean

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_FOLDER = os.path.dirname(SCRIPT_PATH)
CRAWLER_MODULES = {
    "Crawler": Crawler,
    "WanderingInnPatreonCrawler": WanderingInnPatreonCrawler
}
SEPARATOR = 30 * "-" + "\n"


@click.group()
def cli():
    pass


@cli.command()
def interactive():
    questions = [
        {
            "type": "list",
            "message": "Which config do you want to run?",
            "name": "config_name",
            "choices": [{"name": f} for f in get_builtin_configs()]
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

    run_tool(
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
    run_tool(config, download, clean_download, convert, clean_convert, bind, ebook_convert)


def run_tool(config, download, clean_download, convert, clean_convert, bind, ebook_convert):
    config_name = config

    config = load_config(config_name)

    if download:
        echo("Downloading chapters...")
        crawler = CRAWLER_MODULES.get(config.crawler_module, Crawler)(config)
        if clean_download:
            crawler.clean()
        crawler.start_download()

    if convert:
        echo(SEPARATOR + "Converting chapters...")
        converter = Converter(config)
        if clean_convert:
            converter.clean()
        converter.convert_all()

    if bind:
        echo(SEPARATOR + "Binding chapters into eBook...")
        binder = Binder(config)
        binder.bind_book()

    if ebook_convert:
        echo(SEPARATOR + "Creating other eBook formats...")
        for f in config.files.ebook_formats:
            echo("Converting epub into " + f)
            os.system("ebook-convert \"%s\" \"%s\"" % (config.files.epub_file, config.files.epub_file.replace("epub", f)))

    if config.files.copy_book_to:
        echo(SEPARATOR + "Copying files...")
        formats = ["epub"] + config.files.ebook_formats
        for f in formats:
            source = config.files.epub_file.replace("epub", f)
            target = config.files.copy_book_to.replace("epub", f)
            if os.path.isfile(source):
                if os.path.isdir(os.path.dirname(target)):
                    from shutil import copyfile
                    copyfile(source, target)
                    echo("Copied %s to %s" % (os.path.basename(source), os.path.dirname(target)))
                else:
                    echo("Couldn't copy eBook to specified path, directory not found!")
            else:
                echo("%s not found!" % source)


def load_config(config_name):
    if config_name in get_builtin_configs():
        path = os.path.join(SCRIPT_FOLDER, "configs", "%s.yaml" % config_name)
    else:
        path = config_name

    if not os.path.isfile(path):
        echo("Couldn't find config file!")
        sys.exit(1)

    if path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as file:
            config = json.load(file)
    elif path.endswith(".yaml") or path.endswith(".yml"):
        with open(path, "r", encoding="utf-8") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
    else:
        echo("Invalid file extension, only .json and .yaml/.yml are supported!")
        return

    return get_validated_config(config_name, config)


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

    validated.files.working_folder = working_folder
    validated.files.cache_folder = cache_folder
    validated.files.book_folder = book_folder
    validated.files.epub_file = epub_file
    validated.files.cover_file = cover_file
    validated.files.manifest_file = manifest_file

    if not os.path.isdir(working_folder):
        os.mkdir(working_folder)

    if not os.path.isdir(cache_folder):
        os.mkdir(cache_folder)

    if not os.path.isdir(book_folder):
        os.mkdir(book_folder)

    return validated


@cli.command()
@click.option("--info", is_flag=True, help="Load the configs and list more information")
def list_configs():
    """List all configs inside the configs/ folder."""
    echo("Available built-in configs:")
    for c in get_builtin_configs():
        echo(c)


def get_builtin_configs():
    configs = []
    for file in os.listdir(os.path.join(SCRIPT_FOLDER, "configs")):
        if file.endswith(".json") or file.endswith(".yaml"):
            configs.append(file.replace(".json", "").replace(".yaml", ""))
    return configs


@cli.command()
@click.argument("url")
@click.option("--name", type=str, help="Name of the config (file)")
def generate_config(url, name):
    """Generate a config file for a fiction from a support site.

    URL can be either the fictions overview page or a chapter (which will be used as the startUrl config entry).

    Currently supported sites:
    - Royal Road
    """
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


if __name__ == "__main__":
    cli()
