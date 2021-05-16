def fix_metaworld_chronicles_paragraphs(soup, content_el):
    """Some chapters have <div> elements instead of proper <p> paragraphs, so rename all <div> tags to <p>"""
    for el in content_el.find_all("div", recursive=False):
        el.name = "p"


def fix_metaworld_chronicles_single_div(soup, content_el):
    from bs4.element import Tag

    div_el = content_el.select_one("div")
    for e in div_el.contents:
        if type(e) is Tag and e.name == "br":
            continue
        new_p = soup.new_tag("p")
        content_el.append(new_p)
        content_el.append("\n")
        content_el.select_one("p:last-of-type").append(e)
    div_el.decompose()


CHAPTER_FIXES = {
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/494392/chapter-346-bride-and-groom": fix_metaworld_chronicles_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/541710/chapter-368-even-death-may-die": fix_metaworld_chronicles_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/551476/chapter-372-a-little-knowledge": fix_metaworld_chronicles_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/553925/chapter-373-the-burden-of-knowledge": fix_metaworld_chronicles_single_div,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/601164/chapter-389-taking-the-low-road": fix_metaworld_chronicles_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/605224/chapter-390-deep-politics": fix_metaworld_chronicles_paragraphs,
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/623067/chapter-396-bait-and-switch": fix_metaworld_chronicles_paragraphs,
}
