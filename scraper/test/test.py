import requests
from bs4 import BeautifulSoup

API_URL = "https://genshin-impact.fandom.com/api.php"
PAGE_TITLE = "Pavo_Ocellus_Chapter"

# Keep headers simple so the API behaves like with curl
HEADERS = {
    "User-Agent": "curl/8.7.1",  # or any simple UA, not a full Chrome UA
    "Accept": "*/*",
}

session = requests.Session()
session.trust_env = False  # optional: ignore system proxy env vars


def get_sections(page_title: str) -> dict[str, str]:
    """
    Return {section_name: index} for the page.
    """
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "sections",
        "format": "json",
        "formatversion": "2",
    }

    resp = session.get(API_URL, params=params, headers=HEADERS)
    resp.raise_for_status()

    data = resp.json()
    sections: dict[str, str] = {}
    for sec in data["parse"]["sections"]:
        line = sec["line"].strip()
        idx = sec["index"]
        sections[line] = idx
    return sections


def get_section_text(page_title: str, sec_index: str) -> str:
    """
    Fetch one section by index and return plain text.
    """
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "text",
        "section": sec_index,
        "format": "json",
        "formatversion": "2",
    }

    resp = session.get(API_URL, params=params, headers=HEADERS)
    resp.raise_for_status()

    data = resp.json()
    html = data["parse"]["text"]
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)


if __name__ == "__main__":
    sections = get_sections(PAGE_TITLE)
    print("Sections on page:")
    for name, idx in sections.items():
        print(f"  {idx}: {name}")

    # Find "Summary" (exact or case-insensitive)
    summary_index = None
    for name, idx in sections.items():
        if name.lower() == "summary":
            summary_index = idx
            break

    if not summary_index:
        raise SystemExit("No 'Summary' section found")

    summary_text = get_section_text(PAGE_TITLE, summary_index)
    print("\n=== SUMMARY ===\n")
    print(summary_text)
    print("\nSection index:", summary_index)
