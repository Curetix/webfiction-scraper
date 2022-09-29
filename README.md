# Web Fiction Scraper

Scrapes web fictions into an eBook format.

## Installation

You need Python 3.8 or later.

Clone the repository and install:

```bash
pip install .
```

After installation, you can use the scraper:

```bash
webfictionscraper --help
```

## Basics

You'll need a config file to run the scraper:

1) Use one of the built-in config files. List all available configs with ```webfictionscraper list-configs ``` and pick one name.
2) Create your own config file. The built-in config for _The Wandering Inn - Volume 1_ documents all available options.
3) Automatically generate a config by providing a valid fiction URL to the ```webfictionscraper generate-fiction-config``` command.

Once you picked or created a config file, run the scraper:

```bash
webfictionscraper run CONFIG
```

For all available options, use the ```--help``` flag.

Alternatively, use the interactive mode:

```bash
webfictionscraper interactive
```
