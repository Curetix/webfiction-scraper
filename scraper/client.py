import json
import os
import sys
import urllib.parse
import uuid

import yaml
from box import Box
from click import echo, confirm
from schema import Schema, SchemaError

from . import Converter, Binder
from .crawler import Crawler, WanderingInnPatreonCrawler
from .generator import RoyalRoadConfigGenerator
from .const import CONFIG_SCHEMA
from .utils import normalize_string, lowercase_clean

CRAWLER_MODULES = {
    "Crawler": Crawler,
    "WanderingInnPatreonCrawler": WanderingInnPatreonCrawler
}
SEPARATOR = 30 * "-" + "\n"


class FictionScraperClient:
    def __init__(self, client_config, configs_folder, data_folder):
        self.config_overrides = client_config.get("configOverrides", {})
        self.configs_folder = configs_folder
        self.data_folder = data_folder

    def run(self, config_name, download, clean_download, convert, clean_convert, bind, ebook_convert):
        config = self.load_fiction_config(config_name)

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

        if ebook_convert and len(config.files.get("ebook_formats", [])) > 0:
            echo(SEPARATOR + "Creating other eBook formats...")
            for f in config.files.get("ebook_formats", []):
                echo("Converting epub into " + f)
                os.system(
                    "ebook-convert \"%s\" \"%s\"" % (config.files.epub_file, config.files.epub_file.replace("epub", f)))

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

    def load_fiction_config(self, config_name):
        if config_name in self.get_fiction_configs():
            path = os.path.join(self.configs_folder, "%s.yaml" % config_name)
        else:
            path = config_name
            config_name = os.path.basename(config_name).replace(".yaml", "")

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

        if override := self.config_overrides.get(config_name):
            # Supports nested dictionary updates
            def update(d, u):
                import collections.abc
                for k, v in u.items():
                    if isinstance(v, collections.abc.Mapping):
                        d[k] = update(d.get(k, {}), v)
                    else:
                        d[k] = v
                return d

            update(config, override)

        try:
            validated = Schema(CONFIG_SCHEMA).validate(config)
        except SchemaError as e:
            echo(e)
            sys.exit(1)

        validated = Box(validated, camel_killer_box=True, default_box=True)
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
            working_folder = os.path.join(self.data_folder, config_name)
        elif working_folder and not os.path.isabs(working_folder):
            working_folder = os.path.join(self.data_folder, working_folder)

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

    def get_fiction_configs(self):
        configs = []
        for file in os.listdir(self.configs_folder):
            if file.endswith(".json") or file.endswith(".yaml"):
                configs.append(file.replace(".json", "").replace(".yaml", ""))
        return configs

    def generate_fiction_config(self, url, name):
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
            if not confirm("Couldn't validate newly generated config, save anyways?"):
                return

        config.to_yaml(filename=os.path.join(self.configs_folder, "%s.yaml" % name))

        echo("Config for \"%s\" successfully generated, validated and saved!" % config.metadata.title)
        echo("It can now be used with \"client.py run %s\"!" % name)
