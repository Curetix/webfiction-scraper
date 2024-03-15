from setuptools import setup, find_packages

setup(
    name="WebFictionScraper",
    version="1.4.0",
    author="Curetix",
    author_email="me@curetix.eu",
    url="https://gitlab.com/Curetix/python-webfiction-scraper",
    description="Scrape web fictions into eBooks.",
    packages=find_packages(),
    py_modules=["webfictionscraper"],
    install_requires=[
        "beautifulsoup4",
        "click",
        "platformdirs",
        "ebooklib",
        "python-box[all]",
        "questionary",
        "requests",
        "schema"
    ],
    entry_points="""
        [console_scripts]
        webfictionscraper=webfictionscraper:cli
    """,
)