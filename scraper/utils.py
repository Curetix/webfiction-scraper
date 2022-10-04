import os


BASE_DIR = os.path.join(os.path.expanduser("~"), "WebFictionScraper")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIGS_DIR = os.path.join(BASE_DIR, "configs")


def normalize_string(s):
    return (
        "".join([c for c in s if c.isalpha() or c.isdigit() or c == " "])
        .strip()
        .replace("  ", " ")
    )


def lowercase_clean(s):
    return "".join([c for c in s if c.isalpha() or c.isdigit()]).strip().lower()
