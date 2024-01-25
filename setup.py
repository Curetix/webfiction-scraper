from setuptools import setup, find_packages

setup(
    name="WebFictionScraper",
    version="1.4",
    author="Curetix",
    author_email="contact@curetix.eu",
    url="https://gitlab.com/Curetix/python-webfiction-scraper",
    description="Scrape web fictions into eBooks.",
    packages=find_packages(),
    py_modules=["webfictionscraper"],
    package_data={"scraper": ["configs/*.yaml"]},
    install_requires=[
        "ebooklib",
        "pyyaml",
        "click",
        "schema",
        "requests",
        "beautifulsoup4",
        "lxml",
        "python-box[all]>=5.0,<8.0",
        "pyinquirer",
        "appdirs"
    ],
    entry_points="""
        [console_scripts]
        webfictionscraper=webfictionscraper:cli
    """,
)