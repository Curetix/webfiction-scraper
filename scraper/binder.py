import os
from urllib.parse import urlparse

from click import echo
from ebooklib import epub
from requests import get
from click import echo

from .manifest import Manifest
from .const import DC_KEYS


class Binder:
    def __init__(self, config):
        self.config = config
        self.manifest = Manifest(config.files.manifest_file)

    def bind_book(self):
        book = epub.EpubBook()

        for (m, v) in self.config.metadata.items():
            m = m.lower()
            if m in DC_KEYS:
                if m == "identifier":
                    book.set_identifier(v)
                elif m == "title":
                    book.set_title(v)
                elif m == "language":
                    book.set_language(v)
                elif m == "author" or m == "creator":
                    book.add_author(v)
                else:
                    book.add_metadata("DC", m, str(v))
            else:
                book.add_metadata(None, "meta", "", {"name": m, "content": str(v)})

        cover_file = self.config.files.cover_file
        if cover_file:
            url = urlparse(cover_file)
            if all([url.scheme, url.netloc]):
                file_name = os.path.basename(url.path)
                file_path = os.path.join(self.config.files.working_folder, file_name)
                if not os.path.isfile(file_path):
                    echo("Downloading cover image...")
                    r = get(cover_file, stream=True)
                    if r.status_code == 200:
                        with open(file_path, "wb") as file:
                            for chunk in r:
                                file.write(chunk)
                cover_file = file_path

            if os.path.isfile(cover_file):
                with open(cover_file, "rb") as file:
                    book.set_cover(os.path.basename(cover_file), file.read())

        style = "@namespace epub \"http://www.idpf.org/2007/ops\";\n"
        if self.config.style:
            style += self.config.style

        stylesheet = epub.EpubItem(uid="style", file_name="style.css", media_type="text_css", content=style)
        book.add_item(stylesheet)

        chapters = []
        base_folder = self.config.files.book_folder
        for (i, c) in enumerate(filter(lambda x: x.get("converted"), self.manifest)):
            file_name = os.path.basename(c.get("file"))
            chapter = epub.EpubHtml(
                title=c.get("title"),
                file_name=file_name,
                lang=self.config.metadata.language,
            )

            with open(os.path.join(base_folder, file_name), "rb") as file:
                chapter.set_content(file.read())

            chapter.add_item(stylesheet)
            chapters.append(chapter)
            book.add_item(chapter)

        book.toc = tuple(chapters)
        book.spine = chapters

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub.write_epub(self.config.files.epub_file, book, {})

        echo("Created EPUB!")
