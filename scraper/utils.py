import os

from .const import CONFIGS_DIR, USER_CONFIGS_DIR, DATA_DIR


def normalize_string(s):
    return (
        "".join([c for c in s if c.isalpha() or c.isdigit() or c == " "])
        .strip()
        .replace("  ", " ")
    )


def lowercase_clean(s):
    return "".join([c for c in s if c.isalpha() or c.isdigit()]).strip().lower()


def init_data_dir():
    try:
        os.mkdir(DATA_DIR)
        os.mkdir(USER_CONFIGS_DIR)
    except FileExistsError:
        pass


def get_fiction_config(config_name):
    file = "%s.yaml" % config_name
    if os.path.isfile(p := os.path.join(CONFIGS_DIR, file)):
        return p
    elif os.path.isfile(p := os.path.join(USER_CONFIGS_DIR, file)):
        return p
    else:
        return None


def list_fiction_configs():
    configs = []
    if os.path.isdir(CONFIGS_DIR):
        for file in os.listdir(CONFIGS_DIR):
            if file.endswith(".yaml"):
                configs.append(file.replace(".yaml", ""))
    if os.path.isdir(USER_CONFIGS_DIR):
        for file in os.listdir(USER_CONFIGS_DIR):
            if file.endswith(".yaml"):
                configs.append(file.replace(".yaml", ""))
    return configs
