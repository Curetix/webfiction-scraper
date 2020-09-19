import datetime
import os

from appdirs import user_data_dir
from schema import And, Or, Optional


CONFIGS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "configs")
DATA_DIR = user_data_dir("WebFictionScraper", "Curetix")
USER_CONFIGS_DIR = os.path.join(DATA_DIR, "configs")

CONFIG_SCHEMA = {
    "startUrl": And(str, lambda s: s.startswith("http")),
    Optional("endUrl", default=""): And(str, lambda s: s.startswith("http")),
    Optional("skipChapters", default=[]): [str],
    Optional("crawlerModule", default="Crawler"): str,
    "metadata": {
        "title": str,
        "author": str,
        Optional("description"): str,
        Optional("language", default="en"): And(str, lambda s: len(s) == 2),
        Optional("publisher", default="Scrapy eBooks"): str,
        Optional("date"): datetime.date,
        # Allow additional metadata tags
        Optional(str): str,
    },
    Optional("files", default={}): {
        Optional("workingFolder"): str,
        Optional("coverFile"): str,
        Optional("epubFile"): str,
        Optional("ebookFormats", default=[]): [str],
        Optional("copyBookTo", default=""): str
    },
    "selectors": {
        "titleElement": str,
        "contentElement": str,
        "nextChapterElement": str,
        Optional("cutOffElement", default=None): Or(str, [str]),
    },
    Optional("removeEmptyElements", default=True): bool,
    Optional("substitutions", default=[]): [
        {
            "selectorType": lambda s: s == "css" or s == "regex" or s == "text",
            "selector": str,
            Optional("chapterUrl", default=""): str,
            Optional("replaceWith", default=""): str,
        }
    ],
}

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