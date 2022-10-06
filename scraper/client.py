import os
import sys
import uuid
import json
from urllib.parse import urlparse

from box import Box, BoxList
from click import echo, confirm
from schema import Schema, SchemaError
from requests import get

from .converter import Converter
from .binder import Binder
from .crawler import Crawler, WanderingInnPatreonCrawler
from .generator import RoyalRoadConfigGenerator
from .const import FICTION_CONFIG_SCHEMA, CLIENT_CONFIG_SCHEMA
from .utils import BASE_DIR, DATA_DIR, CONFIGS_DIR, normalize_string, lowercase_clean

SEPARATOR = 30 * "-" + "\n"


class FictionScraperClient:
    def __init__(self):
        self.init_directories()
        self.client_config = self.load_client_config()
        self.fiction_schema_config = self.get_fiction_config_schema()

    @staticmethod
    def init_directories():
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(CONFIGS_DIR, exist_ok=True)

    @staticmethod
    def print_paths():
        echo("Base: %s" % BASE_DIR)
        echo("Client config: %s" % os.path.join(BASE_DIR, "client.yaml"))
        echo("Fiction configs: %s" % CONFIGS_DIR)
        echo("Data (downloads, books): %s" % DATA_DIR)

    @staticmethod
    def get_fiction_config_schema() -> str or None:
        file_path = os.path.join(BASE_DIR, "fiction_config.schema.json")
        if not os.path.isfile(file_path):
            r = get('https://raw.githubusercontent.com/Curetix/webfiction-scraper-configs/main/schema/fiction_config.schema.json')

            if r.ok:
                with open(file_path, "wb") as file:
                    file.write(r.content)
                return r.json()
            else:
                return None

        with open(file_path, "r") as file:
            schema = json.load(file)

        return schema

    def run(self, config_name: str, download: bool, clean_download: bool, convert: bool, clean_convert: bool, bind: bool, ebook_convert: bool):
        """Run the scraper with the provided config_name and tasks.

        :param config_name: name or path of fiction config file
        :param download: flag if chapters should be downloaded
        :param clean_download: flag if currently downloaded chapters should be cleared
        :param convert: flag if chapters should be converted
        :param clean_convert: flag if currently converted chapters should be cleared
        :param bind: flag if eBook should be created
        :param ebook_convert: flag if eBook should be converted into configured formats
        """
        config = self.load_fiction_config(config_name)

        if not config:
            echo("Invalid config file!")
            sys.exit(1)

        if not os.path.isdir(f := config.files.working_folder):
            os.mkdir(f)

        if not os.path.isdir(f := config.files.cache_folder):
            os.mkdir(f)

        if not os.path.isdir(f := config.files.book_folder):
            os.mkdir(f)

        if url := config.get("official_book_url"):
            echo("The author %s has published an official book for %s!" % (config.metadata.author, config.metadata.title))
            echo("If you want to support their work, consider purchasing it here:")
            if type(url) is str:
                echo(" %s" % url)
            elif type(url) is BoxList:
                for u in url:
                    echo(" - %s" % u)

        if download or clean_download:
            echo("Downloading chapters...")

            if config.get("crawler_module") == "WanderingInnPatreonCrawler":
                crawler = WanderingInnPatreonCrawler(config, self.client_config.get("patreon_session_cookie"))
            else:
                crawler = Crawler(config)

            if clean_download:
                crawler.clean()
            crawler.start_download()

        if convert or clean_convert or clean_download:
            echo(SEPARATOR + "Converting chapters...")
            converter = Converter(config)
            if clean_download or clean_convert:
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
    def load_client_config() -> Box:
        """Load the client configuration file from the users data directory, if it exists.

        :return: client configuration
        """
        if os.path.isfile(path := os.path.join(BASE_DIR, "client.yaml")):
            config = Box.from_yaml(filename=path, camel_killer_box=True)

            try:
                validated = Schema(CLIENT_CONFIG_SCHEMA).validate(config)
            except SchemaError as e:
                echo(e)
                sys.exit(1)

            return validated

        return Box(config_overrides=Box())

    def load_fiction_config(self, config_name: str) -> Box or None:
        """Load the fiction configuration from the provided config_name, if it exists.

        :param config_name: path or name of fiction config
        :return: validated config
        """
        if os.path.isfile(config_name):
            path = config_name
            config_name = os.path.basename(config_name).replace(".yaml", "")
        elif p := self.get_fiction_config_path(config_name):
            path = p
        else:
            echo("Couldn't find config file!")
            sys.exit(1)

        if not path.endswith(".yaml"):
            echo("Invalid file extension, only .yaml is supported!")
            sys.exit(1)

        config = Box.from_yaml(filename=path, camel_killer_box=True, default_box=True)

        if override := self.client_config.get("config_overrides").get(config_name.lower()):
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
        except SchemaError as error:
            echo("\nValidation failed for config '%s':" % config_name)
            echo(error)
            return None

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
        cover_file_url = urlparse(cover_file)

        if not epub_file:
            epub_file = os.path.join(working_folder, title + ".epub")
        elif epub_file and not os.path.isabs(epub_file):
            epub_file = os.path.join(working_folder, epub_file)

        if not cover_file:
            cover_file = os.path.join(working_folder, "cover.jpg")
        elif all([cover_file_url.scheme, cover_file_url.netloc]):
            pass
        elif cover_file and not os.path.isabs(cover_file):
            cover_file = os.path.join(working_folder, cover_file)

        validated.files.working_folder = working_folder
        validated.files.cache_folder = cache_folder
        validated.files.book_folder = book_folder
        validated.files.epub_file = epub_file
        validated.files.cover_file = cover_file
        validated.files.manifest_file = manifest_file

        return validated

    @staticmethod
    def generate_fiction_config(url, name=None) -> str:
        """Generate a config file for a fiction from a support site.

        :param url: URl of fictions overview page or a chapter (which will be used startUrl)
        :param name: optional name of the config file
        :return: name of the config
        """
        if not url.startswith("http"):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc

        if domain == "royalroad.com" or domain == "www.royalroad.com":
            echo("Detected Royal Road URL!")
            generator = RoyalRoadConfigGenerator(url)
        else:
            echo("Invalid URL or site not supported!")
            sys.exit(1)

        config = generator.get_config()
        if not name:
            name = config.metadata.title

        try:
            Schema(FICTION_CONFIG_SCHEMA).validate(config)
        except SchemaError as e:
            echo(e)
            if not confirm("Couldn't validate newly generated config, save anyways?"):
                sys.exit()

        config.to_yaml(filename=os.path.join(CONFIGS_DIR, "%s.yaml" % name))

        echo("Config for \"%s\" successfully generated, validated and saved!" % config.metadata.title)

        return name

    @staticmethod
    def list_fiction_configs(remote=False) -> [str] or None:
        if remote:
            r = get('https://api.github.com/repos/curetix/webfiction-scraper-configs/contents/configs')

            if r.ok:
                json = r.json()
                configs = [c["name"].replace(".yaml", "") for c in json if c["name"].endswith(".yaml")]
                return configs
            else:
                return None
        else:
            if os.path.isdir(CONFIGS_DIR):
                configs = [f.replace(".yaml", "") for f in os.listdir(CONFIGS_DIR) if f.endswith(".yaml")]
                return configs
            else:
                return None

    @staticmethod
    def get_fiction_config_path(config_name) -> str or None:
        file = "%s.yaml" % config_name
        if os.path.isfile(p := os.path.join(CONFIGS_DIR, file)):
            return p
        else:
            return None

    def download_fiction_config(self, name: str, overwrite=False) -> str or None:
        file_name = "%s.yaml" % name
        file_path = self.get_fiction_config_path(file_name)

        if file_path and not overwrite:
            echo("The file %s already exists in the configs folder. Skipping download." % file_name)
            return
        elif file_path and overwrite:
            echo("The file %s already exists in the configs folder and will be overwritten." % file_name)

        r = get('https://raw.githubusercontent.com/Curetix/webfiction-scraper-configs/main/configs/%s' % file_name)

        if r.ok:
            with open(file_path, "wb") as file:
                file.write(r.content)
            return file_path
