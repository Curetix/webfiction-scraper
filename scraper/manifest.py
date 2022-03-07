import json
from json import JSONDecodeError
import os
from click import echo


class Manifest(list):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.load()

    def load(self):
        if os.path.isfile(self.path):
            with open(os.path.join(self.path), "r", encoding="utf-8") as file:
                try:
                    items = json.load(file)
                except JSONDecodeError as error:
                    echo('Manifest could not be loaded. You might need to use the --clean-download flag.')
            for i in items:
                self.append(i)

    def save(self):
        with open(os.path.join(self.path), "w", encoding="utf-8") as file:
            json.dump(self, file, indent=2)
