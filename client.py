import os
import sys
import uuid

import click
from box import Box
from click import echo
from schema import Schema, SchemaError

from scraper.const import CONFIG_SCHEMA
from scraper.utils import normalize_string, lowercase_clean

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_FOLDER = os.path.dirname(SCRIPT_PATH)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("config")
def run(**kwargs):
    """Run the scraper with the provided CONFIG.

    CONFIG can be a path to a valid JSON or YAML config file,
    or the name of a built-in config. To list all available
    default configs, use the command LIST-CONFIGS.
    """
    config_name = kwargs["config"]

    if config_name in get_builtin_configs():
        path = os.path.join(SCRIPT_FOLDER, "configs", "%s.yaml" % config_name)
    else:
        path = config_name

    if not os.path.isfile(path):
        echo("Couldn't find config file!")
        sys.exit(1)

    if path.endswith(".json"):
        config = Box.from_json(filename=path)
    elif path.endswith(".yaml") or path.endswith(".yml"):
        config = Box.from_yaml(filename=path)
    else:
        echo("Invalid file extension, only .json and .yaml/.yml are supported!")
        sys.exit(1)

    config = get_validated_config(config)

    print(config.startUrl)


def get_validated_config(config: Box):
    validated = Schema(CONFIG_SCHEMA).validate(config)
    files = validated.get("files")
    metadata = validated.get("metadata")
    title = normalize_string(metadata.get("title"))

    if not metadata.get("identifier"):
        ident_string = "%s-%s" % (
            lowercase_clean(metadata.get("author")),
            lowercase_clean(metadata.get("title")),
        )
        validated["metadata"]["identifier"] = uuid.uuid5(
            uuid.NAMESPACE_DNS, ident_string
        )

    if not files.get("workingFolder"):
        files["workingFolder"] = os.path.join(SCRIPT_FOLDER, title)

    if not files.get("epubFile"):
        files["epubFile"] = title + ".epub"

    if not files.get("cacheFolder"):
        files["cacheFolder"] = "cache/"

    if not files.get("bookFolder"):
        files["bookFolder"] = "book/"

    if not os.path.isdir(files["workingFolder"]):
        os.mkdir(files["workingFolder"])

    cache_folder = files.get("cacheFolder")
    cache_folder_path = (
        cache_folder
        if os.path.isabs(cache_folder)
        else os.path.join(files.get("workingFolder"), cache_folder)
    )
    if not os.path.isdir(cache_folder_path):
        os.mkdir(cache_folder_path)

    book_folder = files.get("bookFolder")
    book_folder_path = (
        book_folder
        if os.path.isabs(book_folder)
        else os.path.join(files.get("workingFolder"), book_folder)
    )
    if not os.path.isdir(book_folder_path):
        os.mkdir(book_folder_path)

    for s in validated.get("substitutions"):
        if not s.get("css") and not s.get("regex") and not s.get("text"):
            raise SchemaError("Invalid substitution %s, no selector specified." % s)

    validated["files"] = files

    return validated


def get_builtin_configs():
    configs = []
    for file in os.listdir(os.path.join(SCRIPT_FOLDER, "configs")):
        if file.endswith(".json") or file.endswith(".yaml"):
            configs.append(file.replace(".json", "").replace(".yaml", ""))
    return configs


@cli.command()
def list_configs(**kwargs):
    """List all available built-in configs."""
    echo("Available built-in configs:")
    for c in get_builtin_configs():
        echo(c)


if __name__ == "__main__":
    cli()
