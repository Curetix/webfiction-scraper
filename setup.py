from setuptools import setup, find_packages

setup(
    name="WebFictionScraper",
    version="1.1",
    author="Curetix",
    author_email="hello@curetix.me",
    url="https://gitlab.com/Curetix/python-webfiction-scraper",
    description="Scrape web fiction blogs into eBooks.",
    packages=find_packages(),
    py_modules=["client"],
    package_data={"scraper": ["configs/*.yaml"]},
    install_requires=[
        "ebooklib",
        "pyyaml",
        "click",
        "schema",
        "requests",
        "beautifulsoup4",
        "lxml",
        "python-box[all]>=5.0,<6.0",
        "pyinquirer",
        "appdirs"
    ],
    entry_points="""
        [console_scripts]
        webfictionscraper=client:cli
    """,
)