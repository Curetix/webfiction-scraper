# Web Fiction Scraper

This project aims to easily and quickly turn any Web Fiction into an eBook for your eReader.

## Installation

You need Python 3.8 or later and [Poetry](https://python-poetry.org).

Clone the repository and install:

```bash
poetry install
```

After installation, you can use the scraper:

```bash
webfictionscraper --help
```

## Usage

Run the scraper using a fiction config file:

```bash
webfictionscraper run <CONFIG_NAME>
```

For all available options, use the `--help` flag.

Alternatively, you can start the interactive mode:

```bash
webfictionscraper interactive
```

## Where to get Fiction configs

### Download

Download one, multiple, or all configs from the [config repository](https://github.com/curetix/webfiction-scraper-configs).

List them with `webfictionscraper list-configs --remote`.
Then download them with `webfictionscraper download-config [NAME]`.
Or download them all with `webfictionscraper download-config --all`.

Alternatively, start the interactive mode with `webfictionscraper interactive` and select **Download config(s)**.

### Create your own

Create your own config file. For examples and documentation, see the [config repository](https://github.com/curetix/webfiction-scraper-configs).

### Generate

The scraper can automatically generate configs for fictions on poplar sites like RoyalRoad or FictionPress with the
`webfictionscraper generate-config [URL]` command.

Alternatively, start the interactive mode with `webfictionscraper interactive` and select **Generate config**.
