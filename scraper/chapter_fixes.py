import re
from bs4 import BeautifulSoup


def fix_div_paragraphs(soup: BeautifulSoup, content_el: BeautifulSoup, content_el_selector: str):
    """Some chapters have <div> elements instead of proper <p> paragraphs, so rename all <div> tags to <p>"""
    for el in content_el.find_all("div", recursive=False):
        el.name = "p"


def unwrap_div(soup: BeautifulSoup, content_el: BeautifulSoup, content_el_selector: str):
    """Unwrap the first div element"""
    el = content_el.select_one("div")
    if el is not None:
        el.unwrap()


def unwrap_article(soup: BeautifulSoup, content_el: BeautifulSoup, content_el_selector: str):
    """Unwrap the first article element"""
    el = content_el.select_one("article")
    if el is not None:
        el.unwrap()


def unwrap_toplevel_divs(soup: BeautifulSoup, content_el: BeautifulSoup, content_el_selector: str):
    """Unwrap all divs at content element root level"""
    while (el := content_el.select_one(content_el_selector + " > div")) is not None and content_el.select_one(content_el_selector + " > p") is None:
        el.unwrap()


def unwrap_toplevel_divs_alt(soup: BeautifulSoup, content_el: BeautifulSoup, content_el_selector: str):
    divs = content_el.select(content_el_selector + " > div")
    for el in divs:
        el.unwrap()


def fix_nested_div_paragraphs(soup: BeautifulSoup, content_el: BeautifulSoup, content_el_selector: str):
    # Unwrap the top-level <div>s
    for el in content_el.find_all(content_el_selector + " > div"):
        el.unwrap()
    # Convert the new top-level <div>s in <p>s
    return fix_div_paragraphs(soup, content_el, content_el_selector)


def fix_blockquote_and_div(soup: BeautifulSoup, content_el: BeautifulSoup, content_el_selector: str):
    """Unwrap blockquotes that include a div"""
    content_el.select_one("blockquote > div").unwrap()
    return unwrap_div(soup, content_el, content_el_selector)


# Regex to find the class name of the hidden warning paragraph
rr_warning_pattern = re.compile(r"(\.\w+)\s*\{\s*\n*display:\s*none;\s*\n*speak:\s*never;\s*\n*}")


def remove_piracy_paragraphs(soup: BeautifulSoup, content_el: BeautifulSoup, content_el_selector: str):
    """Remove hidden stolen warning paragraphs from Royal Road chapters"""
    bad_class_match = rr_warning_pattern.findall(str(soup))
    if len(bad_class_match) > 0:
        for element in content_el.find_all(None, {"class": bad_class_match[0].replace(".", "")}):
            element.decompose()


CHAPTER_FIXES = {
    "https://www.royalroad.com/": remove_piracy_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/494392/chapter-346-bride-and-groom": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/541710/chapter-368-even-death-may-die": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/551476/chapter-372-a-little-knowledge": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/601164/chapter-389-taking-the-low-road": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/605224/chapter-390-deep-politics": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/623067/chapter-396-bait-and-switch": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/26675/a-journey-of-black-and-red/chapter/407352/22-the-waiting-maw": unwrap_toplevel_divs,
    "https://www.royalroad.com/fiction/26675/a-journey-of-black-and-red/chapter/426349/34-ring-breaker": fix_nested_div_paragraphs,
    "https://www.royalroad.com/fiction/36735/the-perfect-run/chapter/576217/8-past-fragment-len": fix_blockquote_and_div,
    "https://www.royalroad.com/fiction/41033/kairos-a-greek-myth-litrpg/chapter/677603/26-the-wedding": unwrap_toplevel_divs_alt,
    "https://www.royalroad.com/fiction/47557/underland/chapter/775480/8-vernburg": unwrap_toplevel_divs,
}
