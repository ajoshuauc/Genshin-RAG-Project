# scripts/harvest_artifact_lore.py
from __future__ import annotations
import os
import sys
import json
from typing import Set, List, Dict
from urllib.parse import unquote
from bs4 import BeautifulSoup

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scraper.pipeline.harvest.mediawiki import MediaWikiClient, MediaWikiError


def get_data_dir() -> str:
    scraper_data = os.path.join(project_root, "scraper", "data")
    root_data = os.path.join(project_root, "data")
    if os.path.exists(scraper_data):
        return scraper_data
    if os.path.exists(root_data):
        return root_data
    return scraper_data


def extract_artifact_links_from_table(html: str, base_url: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    titles: Set[str] = set()

    table = soup.select_one("table.wikitable.sortable.tdc2.tdc3.jquery-tablesorter")

    def table_matches(table) -> bool:
        class_attr = table.get("class")
        if isinstance(class_attr, list):
            class_tokens = set(class_attr)
        elif isinstance(class_attr, str):
            class_tokens = set(class_attr.split())
        else:
            class_tokens = set()

        required_sets = [
            {"wikitable", "sortable", "tdc2", "tdc3", "jquery-tablesorter"},
            {"wikitable", "sortable", "tdc2", "tdc3"},
            {"wikitable", "sortable", "tdc3", "jquery-tablesorter"},
        ]
        return any(required.issubset(class_tokens) for required in required_sets)

    if not table:
        for candidate in soup.find_all("table"):
            if table_matches(candidate):
                table = candidate
                break

    if not table:
        # Fallback: locate table whose headers match Name/Quality/Pieces/Bonuses
        header_target = {"Name", "Quality", "Pieces", "Bonuses"}
        for candidate in soup.find_all("table"):
            headers = {th.get_text(strip=True) for th in candidate.find_all("th")}
            if header_target.issubset(headers):
                table = candidate
                break

    if not table:
        print("Warning: artifact table with target classes was not found")
        return titles

    tbody = table.find("tbody")
    if not tbody:
        print("Warning: tbody missing in artifact table")
        return titles

    rows = tbody.find_all("tr")

    for row in rows:
        first_cell = row.find("td")
        if not first_cell:
            continue
        link = first_cell.find("a", href=True)
        if not link:
            continue

        href_attr = link.get("href", "")
        href = ""
        if isinstance(href_attr, list):
            href = str(href_attr[0]) if href_attr else ""
        else:
            href = str(href_attr)

        if not href:
            continue

        wiki_path = None
        if href.startswith("./"):
            wiki_path = "/wiki/" + href[2:]
        elif href.startswith("/wiki/"):
            wiki_path = href
        elif base_url in href and "/wiki/" in href:
            wiki_path = "/wiki/" + href.split("/wiki/", 1)[1]

        if not wiki_path:
            continue

        if any(
            wiki_path.startswith(prefix)
            for prefix in (
                "/wiki/File:",
                "/wiki/Category:",
                "/wiki/Template:",
                "/wiki/User:",
                "/wiki/Help:",
                "/wiki/Special:",
            )
        ):
            continue

        title_part = wiki_path.replace("/wiki/", "").split("#")[0]
        if not title_part:
            continue

        title = unquote(title_part).replace("_", " ")
        if title:
            normalized = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
            titles.add(normalized)

    return titles


def extract_lore_sections_from_html(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    lore_sections: List[str] = []

    def heading_text(tag) -> str:
        headline = tag.find("span", class_="mw-headline")
        if headline:
            return headline.get_text(strip=True)
        return tag.get_text(" ", strip=True)

    def heading_level(tag) -> int:
        name = getattr(tag, "name", "")
        if isinstance(name, str) and len(name) == 2 and name.startswith("h") and name[1].isdigit():
            return int(name[1])
        return 7

    def collect_block_text(container) -> List[str]:
        parts: List[str] = []
        for node in container:
            if isinstance(node, str):
                text = node.strip()
            elif getattr(node, "name", None) in {"p", "ul", "ol", "dl", "blockquote"}:
                text = node.get_text("\n", strip=True)
            elif hasattr(node, "get_text"):
                text = node.get_text("\n", strip=True)
            else:
                text = ""
            if text:
                parts.append(text)
        return parts

    lore_headings = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        text = heading_text(heading)
        text_str = str(text) if text is not None else ""
        if text_str and text_str.lower().startswith("lore"):
            lore_headings.append(heading)

    for heading in lore_headings:
        level = heading_level(heading)
        section_parts: List[str] = []
        for sibling in heading.find_next_siblings():
            if getattr(sibling, "name", None) and str(sibling.name).startswith("h"):
                if heading_level(sibling) <= level:
                    break
            if sibling.name in {"p", "ul", "ol", "dl", "blockquote"}:
                text = sibling.get_text("\n", strip=True)
            elif hasattr(sibling, "get_text"):
                text = sibling.get_text("\n", strip=True)
            else:
                text = sibling.strip() if isinstance(sibling, str) else ""
            if text:
                section_parts.append(text)
        if section_parts:
            lore_sections.append("\n\n".join(section_parts))

    if lore_sections:
        return lore_sections

    for tab in soup.select(".tabbertab[title]"):
        title = tab.get("title", "")
        title_str = str(title) if title is not None else ""
        if title_str and title_str.lower().startswith("lore"):
            parts = collect_block_text(tab.children)
            if parts:
                lore_sections.append("\n\n".join(parts))

    if lore_sections:
        return lore_sections

    for item in soup.select(".pi-item[data-source='lore'], .pi-data[data-source='lore'], [data-source='lore']"):
        value = item.select_one(".pi-data-value")
        text = (value or item).get_text("\n", strip=True)
        if text:
            lore_sections.append(text)

    return lore_sections


def extract_artifact_lore(mw: MediaWikiClient, artifact_title: str) -> str:
    try:
        page_html = mw.page_html(artifact_title)
    except MediaWikiError as exc:
        print(f"Warning: failed to fetch {artifact_title}: {exc}")
        return ""

    if not page_html:
        print(f"Warning: empty response for {artifact_title}")
        return ""

    sections = extract_lore_sections_from_html(page_html)
    combined = "\n\n---\n\n".join(sections).strip()
    return combined


def load_processed_artifacts(out_path: str) -> Set[str]:
    processed: Set[str] = set()
    if not os.path.exists(out_path):
        return processed
    try:
        with open(out_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list):
                for record in data:
                    name = record.get("artifact")
                    if isinstance(name, str):
                        processed.add(name)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: could not read {out_path}: {exc}")
    return processed


def main() -> None:
    mw = MediaWikiClient(
        user_agent=os.getenv("USER_AGENT", "genshin-rag/1.0 (contact: ajoshuauc@gmail.com)"),
        base_url=os.getenv("WIKI_BASE", "https://genshin-impact.fandom.com"),
    )

    data_dir = get_data_dir()
    summaries_dir = os.path.join(data_dir, "interim", "summaries")
    os.makedirs(summaries_dir, exist_ok=True)

    out_path = os.path.join(summaries_dir, "artifact_lore.json")
    processed = load_processed_artifacts(out_path)
    print(f"Found {len(processed)} artifacts already processed")

    artifact_list_title = os.getenv("ARTIFACT_TABLE_TITLE", "Artifact/Sets")
    print(f"Fetching {artifact_list_title} page for artifact table...")
    try:
        list_html = mw.page_html(artifact_list_title)
    except MediaWikiError as exc:
        print(f"Error: failed to fetch {artifact_list_title}: {exc}")
        return

    if not list_html:
        print(f"Error: empty HTML for {artifact_list_title}")
        return

    artifact_titles = extract_artifact_links_from_table(list_html, mw.base_url)
    print(f"Extracted {len(artifact_titles)} artifact links from table")

    remaining = [title for title in artifact_titles if title not in processed]
    skipped = len(artifact_titles) - len(remaining)
    if skipped:
        print(f"Skipping {skipped} artifacts that are already stored")

    artifact_data: List[Dict[str, str]] = []
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as handle:
                existing = json.load(handle)
                if isinstance(existing, list):
                    artifact_data = existing
                    existing_titles = {entry.get("artifact") for entry in artifact_data}
                    remaining = [title for title in remaining if title not in existing_titles]
                    print(f"Resuming: {len(artifact_data)} records on disk, {len(remaining)} left to fetch")
        except (json.JSONDecodeError, OSError):
            print("Warning: unable to load existing artifact data; starting fresh")

    if not remaining:
        print(f"All {len(artifact_titles)} artifacts already processed -> {out_path}")
        return

    save_interval = 10
    new_count = 0

    for artifact_title in tqdm(remaining, desc="Processing artifacts", unit="artifact"):
        try:
            lore_text = extract_artifact_lore(mw, artifact_title)
        except MediaWikiError as exc:
            print(f"Warning: error while fetching lore for {artifact_title}: {exc}")
            lore_text = ""

        if not lore_text:
            print(f"Warning: no lore text found for {artifact_title}")

        record = {
            "artifact": artifact_title,
            "url": mw.canonical_url(mw.base_url, artifact_title),
            "text": lore_text,
        }
        artifact_data.append(record)
        new_count += 1

        if len(artifact_data) % save_interval == 0:
            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump(artifact_data, handle, ensure_ascii=False, indent=2)

    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(artifact_data, handle, ensure_ascii=False, indent=2)

    print(f"Processed {new_count} new artifacts ({skipped} skipped, {len(artifact_titles)} total) -> {out_path}")


if __name__ == "__main__":
    main()
