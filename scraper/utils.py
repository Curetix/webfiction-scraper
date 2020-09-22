import os
from shutil import copyfile

from .const import CONFIGS_DIR, USER_CONFIGS_DIR, DATA_DIR, ROOT_DIR, FIXES_MODULE_DIR


def normalize_string(s):
    return (
        "".join([c for c in s if c.isalpha() or c.isdigit() or c == " "])
        .strip()
        .replace("  ", " ")
    )


def lowercase_clean(s):
    return "".join([c for c in s if c.isalpha() or c.isdigit()]).strip().lower()


def init_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        os.mkdir(USER_CONFIGS_DIR)
    except FileExistsError:
        pass

    try:
        os.mkdir(FIXES_MODULE_DIR)
    except FileExistsError:
        pass

    fixes_file = os.path.join(FIXES_MODULE_DIR, "chapter_fixes.py")

    if os.path.isfile(fixes_file):
        copyfile(fixes_file, fixes_file + ".bak")

    copyfile(os.path.join(ROOT_DIR, "chapter_fixes.py"), fixes_file)


def get_fiction_config(path, user_dir=False):
    path = os.path.join(USER_CONFIGS_DIR if user_dir else CONFIGS_DIR, path)
    if os.path.isfile(path):
        return path
    else:
        return None


def list_fiction_configs(user_dir=False):
    configs = []
    for file in os.listdir(USER_CONFIGS_DIR if user_dir else CONFIGS_DIR):
        if file.endswith(".yaml"):
            configs.append(file.replace(".yaml", ""))
    return configs
