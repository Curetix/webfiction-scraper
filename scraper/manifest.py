import json
import os


class Manifest(list):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.load()

    def load(self):
        if os.path.isfile(self.path):
            with open(os.path.join(self.path), "r") as file:
                items = json.load(file)
            for i in items:
                self.append(i)

    def save(self):
        with open(os.path.join(self.path), "w") as file:
            json.dump(self, file, indent=2)
