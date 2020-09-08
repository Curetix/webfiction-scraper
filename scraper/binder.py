import os
import uuid

from ebooklib import epub

from scraper.const import DC_KEYS


class Binder:
    def __init__(self, config):
        self.config = config
        pass

    def get_path(self, path):
        paths = self.config.get("files")
        return path if os.path.isabs(path) else os.path.join(paths.get("workingFolder"), path)

    def bind_book(self, manifest):
        book = epub.EpubBook()

        for (m, v) in self.config.get("metadata"):
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
                    book.add_metadata("DC", m, v)
            else:
                book.add_metadata(None, "meta", "", {"name": m, "content": v})

        cover_file = self.config.get("files").get("coverFile", "none.jpg")
        cover_file_path = self.get_path(cover_file)
        if cover_file and os.path.isfile(cover_file_path):
            with open(cover_file_path, "rb") as file:
                book.set_cover(os.path.basename(cover_file), file.read())

        chapters = []
        base_folder = self.get_path(self.config.get("files").get("bookFolder"))
        for (i, c) in enumerate([c for c in manifest if c.get("converted", False)]):
            file_name = os.path.basename(c.get("file"))
            chapter = epub.EpubHtml(
                title=c.get("title"),
                file_name=file_name,
                lang=self.config.get("metadata").get("language", "en"),
            )
            with open(os.path.join(base_folder, file_name), "rb") as file:
                chapter.set_content(file.read())
            chapters.append(chapter)
            book.add_item(chapter)

        book.toc = tuple(chapters)
        book.spine = chapters
