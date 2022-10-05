import os

from appdirs import user_data_dir

BASE_DIR = user_data_dir("WebFictionScraper", "Curetix")
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
