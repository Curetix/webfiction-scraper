def fix_div_paragraphs(soup, content_el):
    """Some chapters have <div> elements instead of proper <p> paragraphs, so rename all <div> tags to <p>"""
    for el in content_el.find_all("div", recursive=False):
        el.name = "p"


def unwrap_div(soup, content_el):
    div_el = content_el.select_one("div")
    if div_el is not None:
        div_el.unwrap()


def fix_nested_divs(soup, content_el):
    while (div_el := content_el.select_one("div")) is not None:
        div_el.unwrap()


def fix_nested_div_paragraphs(soup, content_el):
    from bs4.element import Tag
    for el in content_el.contents:
        if type(el) is Tag and el.name == "div":
            el.unwrap()
    return fix_div_paragraphs(soup, content_el)


def fix_blockquote_and_div(soup, content_el):
    content_el.select_one("blockquote > div").unwrap()
    return unwrap_div(soup, content_el)


CHAPTER_FIXES = {
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/494392/chapter-346-bride-and-groom": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/541710/chapter-368-even-death-may-die": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/551476/chapter-372-a-little-knowledge": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/601164/chapter-389-taking-the-low-road": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/605224/chapter-390-deep-politics": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/623067/chapter-396-bait-and-switch": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/26675/a-journey-of-black-and-red/chapter/407352/22-the-waiting-maw": fix_nested_divs,
    "https://www.royalroad.com/fiction/26675/a-journey-of-black-and-red/chapter/426349/34-ring-breaker": fix_nested_div_paragraphs,
    "https://www.royalroad.com/fiction/36735/the-perfect-run/chapter/576217/8-past-fragment-len": fix_blockquote_and_div,
}
