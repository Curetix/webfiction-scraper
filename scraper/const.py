import datetime
import os


from schema import And, Or, Optional


CONFIGS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "configs")
DATA_DIR = os.path.expanduser("~/WebFictionScraper")
USER_CONFIGS_DIR = os.path.join(DATA_DIR, "configs")

CLIENT_CONFIG_SCHEMA = {
    Optional("patreon_session_cookie", default=None): str,
    Optional("config_overrides", default={}): dict,
    Optional("monitored_fictions", default=[]): [
        {
            "rss_feed_url": And(str, lambda s: s.startswith("http")),
            "config_name": str
        }
    ]
}

FICTION_CONFIG_SCHEMA = {
    Optional("official_book_url"): Or(str, [str]),
    "start_url": And(str, lambda s: s.startswith("http")),
    Optional("end_url", default=""): And(str, lambda s: s.startswith("http")),
    Optional("skip_urls", default=[]): [str],
    Optional("crawler_module", default="Crawler"): str,
    "metadata": {
        "title": str,
        "author": str,
        Optional("description"): str,
        Optional("language", default="en"): And(str, lambda s: len(s) == 2),
        Optional("publisher", default="Web Fiction Scraper"): str,
        Optional("date"): datetime.date,
        # Allow additional metadata tags
        Optional(str): str,
    },
    Optional("files", default={}): {
        Optional("working_folder"): str,
        Optional("cover_file"): str,
        Optional("epub_file"): str,
        Optional("ebook_formats", default=[]): [str],
        Optional("copy_book_to", default=""): str
    },
    "selectors": {
        "title_element": str,
        "content_element": str,
        "next_chapter_element": str,
        Optional("cut_off_element", default=None): Or(str, [str]),
    },
    Optional("skip_conversion", default=False): bool,
    Optional("remove_empty_elements", default=True): bool,
    Optional("substitutions", default=[]): [
        {
            "selector_type": lambda s: s == "css" or s == "regex" or s == "text",
            "selector": str,
            Optional("chapter_url", default=""): str,
            Optional("replace_with", default=""): str,
        }
    ],
    Optional("style", default=None): str,
}

# Valid metadata keys
DC_KEYS = [
    "author",
    "contributor",
    "coverage",
    "creator",
    "date",
    "description",
    "format",
    "identifier",
    "language",
    "publisher",
    "relation",
    "rights",
    "source",
    "subject",
    "title",
    "type",
]

CHAPTER_DOC = """<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" />
</head>
<body></body>
</html>
"""