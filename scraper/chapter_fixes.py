def fix_div_paragraphs(soup, content_el, content_el_selector):
    """Some chapters have <div> elements instead of proper <p> paragraphs, so rename all <div> tags to <p>"""
    for el in content_el.find_all("div", recursive=False):
        el.name = "p"


def unwrap_div(soup, content_el, content_el_selector):
    el = content_el.select_one("div")
    if el is not None:
        el.unwrap()


def unwrap_article(soup, content_el, content_el_selector):
    el = content_el.select_one("article")
    if el is not None:
        el.unwrap()


def unwrap_toplevel_divs(soup, content_el, content_el_selector):
    while (el := content_el.select_one(content_el_selector + " > div")) is not None and content_el.select_one(content_el_selector + " > p") is None:
        el.unwrap()


def fix_nested_div_paragraphs(soup, content_el, content_el_selector):
    # Unwrap the top-level <div>s
    for el in content_el.find_all(content_el_selector + " > div"):
        el.unwrap()
    # Convert the new top-level <div>s in <p>s
    return fix_div_paragraphs(soup, content_el, content_el_selector)


def fix_blockquote_and_div(soup, content_el, content_el_selector):
    content_el.select_one("blockquote > div").unwrap()
    return unwrap_div(soup, content_el, content_el_selector)


CHAPTER_FIXES = {
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/494392/chapter-346-bride-and-groom": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/541710/chapter-368-even-death-may-die": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/551476/chapter-372-a-little-knowledge": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/601164/chapter-389-taking-the-low-road": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/605224/chapter-390-deep-politics": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/623067/chapter-396-bait-and-switch": fix_div_paragraphs,
    "https://www.royalroad.com/fiction/26675/a-journey-of-black-and-red/chapter/407352/22-the-waiting-maw": unwrap_toplevel_divs,
    "https://www.royalroad.com/fiction/26675/a-journey-of-black-and-red/chapter/426349/34-ring-breaker": fix_nested_div_paragraphs,
    "https://www.royalroad.com/fiction/36735/the-perfect-run/chapter/576217/8-past-fragment-len": fix_blockquote_and_div,
}
