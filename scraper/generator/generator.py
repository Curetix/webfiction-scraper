from box import Box


class ConfigGenerator:
    def __init__(self, start_url, end_url=None):
        self.config = Box(start_url=start_url)

        if end_url:
            self.config.end_url = end_url

        self.config.metadata = self.get_metadata()
        self.config.selectors = self.get_selectors()

    def get_config(self):
        return self.config

    def get_metadata(self):
        return Box()

    def get_selectors(self):
        return Box()
