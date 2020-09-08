import datetime

from schema import And, Optional


CONFIG_SCHEMA = {
    "startUrl": And(str, lambda s: s.startswith("http")),
    Optional("endUrl"): And(str, lambda s: s.startswith("http")),
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
        Optional("cacheFolder", default="cache/"): str,
        Optional("bookFolder", default="book/"): str,
    },
    "selectors": {
        "titleElement": str,
        "contentElement": str,
        "nextChapterElement": str,
    },
    Optional("removeEmptyElements", default=True): bool,
    Optional("substitutions", default=[]): [
        {
            Optional("chapterUrl"): str,
            Optional("css"): str,
            Optional("regex"): str,
            # TODO: rename text to html?
            Optional("text"): str,
            Optional("replaceWith"): lambda s: s is None or s is str,
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
