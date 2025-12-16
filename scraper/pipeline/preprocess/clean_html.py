# pipeline/preprocess/clean_html.py
from bs4 import BeautifulSoup

REMOVE_SELECTORS = [
    "table", 
    ".portable-infobox", 
    ".navbox", 
    ".infobox",
    # References and citations
    ".reference",
    ".mw-references-wrap",
    ".mw-cite-backlink",
    # Images and galleries
    ".thumb",
    ".gallery",
    # Navigation/metadata
    ".dablink",
    ".hatnote",
    # Scripts and styles (defensive)
    "script",
    "style",
]

def html_to_markdownish(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for sel in REMOVE_SELECTORS:
        for el in soup.select(sel):
            el.decompose()

    lines = []
    for node in soup.find_all(["h2","h3","h4","p","li"]):
        text = node.get_text(" ", strip=True)
        if not text:
            continue
        if node.name == "h2": lines.append(f"## {text}")
        elif node.name == "h3": lines.append(f"### {text}")
        elif node.name == "h4": lines.append(f"#### {text}")
        else: lines.append(text)
    return "\n".join(lines)
