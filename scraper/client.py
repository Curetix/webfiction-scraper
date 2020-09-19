import os
import sys
import urllib.parse
import uuid

from box import Box
from click import echo, confirm
from schema import Schema, SchemaError

from .converter import Converter
from .binder import Binder
from .crawler import Crawler, WanderingInnPatreonCrawler
from .generator import RoyalRoadConfigGenerator
from .const import FICTION_CONFIG_SCHEMA, DATA_DIR, USER_CONFIGS_DIR, CLIENT_CONFIG_SCHEMA
from .utils import normalize_string, lowercase_clean, get_fiction_config

SEPARATOR = 30 * "-" + "\n"


class FictionScraperClient:
    def __init__(self):
        self.client_config = self.load_client_config()

    def run(self, config_name, download, clean_download, convert, clean_convert, bind, ebook_convert):
        config = self.load_fiction_config(config_name)

        if download:
            echo("Downloading chapters...")

            if config.get("crawler_module") == "WanderingInnPatreonCrawler":
                crawler = WanderingInnPatreonCrawler(config, self.client_config.patreon_session_cookie)
            else:
                crawler = Crawler(config)

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

        if config.files.get("copy_book_to"):
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

    @staticmethod
    def load_client_config():
        if not os.path.isdir(DATA_DIR):
            os.makedirs(os.path.join(DATA_DIR, "configs"))

        if os.path.isfile(path := os.path.join(DATA_DIR, "client.yaml")):
            config = Box.from_yaml(filename=path, camel_killer_box=True)

            try:
                validated = Schema(CLIENT_CONFIG_SCHEMA).validate(config)
            except SchemaError as e:
                echo(e)
                sys.exit(1)

            return validated

        return Box()

    def load_fiction_config(self, config_name):
        if os.path.isfile(config_name):
            path = config_name
            config_name = os.path.basename(config_name).replace(".yaml", "")
        elif p := get_fiction_config("%s.yaml" % config_name):
            path = p
        elif p := get_fiction_config("%s.yaml" % config_name, user_dir=True):
            path = p
        else:
            echo("Couldn't find config file!")
            sys.exit(1)

        if not path.endswith(".yaml"):
            echo("Invalid file extension, only .yaml is supported!")
            sys.exit(1)

        config = Box.from_yaml(filename=path, camel_killer_box=True, default_box=True)

        if override := self.client_config.config_overrides.get(config_name.lower()):
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
            validated = Schema(FICTION_CONFIG_SCHEMA).validate(config)
        except SchemaError as e:
            echo(e)
            sys.exit(1)

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
            working_folder = os.path.join(DATA_DIR, config_name)
        elif working_folder and not os.path.isabs(working_folder):
            working_folder = os.path.join(DATA_DIR, working_folder)

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

    @staticmethod
    def generate_fiction_config(url, name):
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
            Schema(FICTION_CONFIG_SCHEMA).validate(config)
        except SchemaError as e:
            echo(e)
            if not confirm("Couldn't validate newly generated config, save anyways?"):
                return

        config.to_yaml(filename=os.path.join(USER_CONFIGS_DIR, "%s.yaml" % name))

        echo("Config for \"%s\" successfully generated, validated and saved!" % config.metadata.title)
        echo("It can now be used with \"client.py run %s\"!" % name)
