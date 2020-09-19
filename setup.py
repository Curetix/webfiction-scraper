from setuptools import setup, find_packages

setup(
    name="WebFictionScraper",
    version="1.0",
    py_modules=["client", "scraper"],
    entry_points="""
        [console_scripts]
        webficscraper=client:cli
    """,
)