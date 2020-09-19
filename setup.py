from setuptools import setup, find_packages

setup(
    name="WebFictionScraper",
    version="1.0",
    py_modules=["client", "scraper"],
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
        webficscraper=client:cli
    """,
)