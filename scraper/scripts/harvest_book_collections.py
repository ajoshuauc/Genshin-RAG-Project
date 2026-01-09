# scripts/harvest_book_collections.py
from __future__ import annotations
import os
import json
import sys
from typing import Set, List, Dict, Optional
from urllib.parse import unquote
from tqdm import tqdm
from bs4 import BeautifulSoup

# Add project root to path for importing modules
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scraper.pipeline.harvest.mediawiki import MediaWikiClient, MediaWikiError


def get_data_dir():
    """Find the data directory, checking scraper/data first, then project_root/data."""
    scraper_data = os.path.join(project_root, "scraper", "data")
    root_data = os.path.join(project_root, "data")
    if os.path.exists(scraper_data):
        return scraper_data
    elif os.path.exists(root_data):
        return root_data
    else:
        return scraper_data


def extract_book_links_from_table(html: str, base_url: str) -> Set[str]:
    """
    Extract book collection page titles from the Book page's table.
    Looks for the table with class "article-table sortable jquery-tablesorter"
    and extracts links from the Title column.
    Returns a set of page titles (normalized).
    """
    soup = BeautifulSoup(html, "html.parser")
    titles = set()
    
    # Find the table with the specified class
    def has_table_classes(classes):
        if not classes:
            return False
        class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
        return "article-table" in class_str and "sortable" in class_str
    
    table = soup.find("table", class_=has_table_classes)
    if not table:
        print("⚠️  Warning: Could not find article-table sortable table")
        return titles
    
    # Find all rows in tbody
    tbody = table.find("tbody")
    if not tbody:
        print("⚠️  Warning: Could not find tbody in table")
        return titles
    
    rows = tbody.find_all("tr")
    print(f"🔍 Found {len(rows)} rows in book collections table")
    
    for row in rows:
        # The Title column is typically the second column (index 1)
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        
        # Look for links in the Title column (second cell)
        title_cell = cells[1]
        link = title_cell.find("a", href=True)
        if not link:
            continue
        
        href_attr = link.get("href", "")
        # Convert to string if it's a list (BeautifulSoup can return lists)
        if isinstance(href_attr, list):
            href = str(href_attr[0]) if href_attr else ""
        else:
            href = str(href_attr) if href_attr else ""
        
        if not href:
            continue
        
        # Extract page title from href
        # Handle relative paths (./), absolute (/wiki/...), and full URLs
        wiki_path = None
        if href.startswith("./"):
            wiki_path = "/wiki/" + href[2:]
        elif href.startswith("/wiki/"):
            wiki_path = href
        elif base_url in href and "/wiki/" in href:
            wiki_path = "/wiki/" + href.split("/wiki/", 1)[1]
        
        if not wiki_path:
            continue
        
        # Skip special pages
        if (wiki_path.startswith("/wiki/File:") or 
            wiki_path.startswith("/wiki/Category:") or 
            wiki_path.startswith("/wiki/Template:") or
            wiki_path.startswith("/wiki/User:") or
            wiki_path.startswith("/wiki/Help:") or
            wiki_path.startswith("/wiki/Special:")):
            continue
        
        # Extract page title from href
        title_part = wiki_path.replace("/wiki/", "").split("#")[0]
        if not title_part:
            continue
        
        # URL decode and normalize
        title = unquote(title_part).replace("_", " ")
        
        # MediaWiki title normalization: first letter uppercase
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
            titles.add(title)
    
    return titles


def get_section_html_via_api(mw: MediaWikiClient, title: str, section_index: str) -> Optional[str]:
    """
    Get a specific section's HTML via MediaWiki API.
    Similar to page_section_text_via_api but returns HTML instead of plain text.
    """
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "section": section_index,
        "format": "json",
        "formatversion": "2",
    }
    
    try:
        resp = mw._request("GET", mw.api_url, params=params)
        data = resp.json()
        
        parse_data = data.get("parse", {})
        if "missing" in parse_data or "error" in data:
            return None
            
        html = parse_data.get("text", "")
        return html if html else None
    except (MediaWikiError, KeyError, ValueError):
        return None


def extract_vol_sections(mw: MediaWikiClient, title: str) -> List[Dict[str, str]]:
    """
    Extract text content under h2 headings that contain "Vol" text using MediaWiki API.
    The h2 headings have class "mw-headline".
    All text is inside <p> tags.
    Returns a list of dicts with 'volume' (heading text) and 'content' (text under heading).
    """
    volumes = []
    
    # Get all sections via API
    sections = mw.page_sections_via_api(title)
    if not sections:
        return volumes
    
    # Find sections that contain "Vol" in their name
    vol_sections = {name: idx for name, idx in sections.items() if "Vol" in name}
    
    for vol_name, section_idx in vol_sections.items():
        # Get the section HTML via API
        section_html = get_section_html_via_api(mw, title, section_idx)
        if not section_html:
            continue
        
        # Parse HTML and extract text from <p> tags
        soup = BeautifulSoup(section_html, "html.parser")
        paragraphs = soup.find_all("p")
        
        # Extract text from all <p> tags
        content_parts = []
        for p in paragraphs:
            text = p.get_text("\n", strip=True)
            if text:
                content_parts.append(text)
        
        content = "\n\n".join(content_parts) if content_parts else ""
        
        if content.strip():
            volumes.append({
                "volume": vol_name,
                "content": content.strip()
            })
    
    return volumes


def load_processed_books(out_path: str) -> Set[str]:
    """Load book titles that have already been processed from the JSON file."""
    processed = set()
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for rec in data:
                        if "title" in rec:
                            processed.add(rec["title"])
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Warning: Could not read existing file {out_path}: {e}")
    return processed


def main():
    mw = MediaWikiClient(
        user_agent=os.getenv("USER_AGENT", "genshin-rag/1.0 (contact: ajoshuauc@gmail.com)"),
        base_url=os.getenv("WIKI_BASE", "https://genshin-impact.fandom.com"),
    )
    
    data_dir = get_data_dir()
    summaries_dir = os.path.join(data_dir, "interim", "summaries")
    os.makedirs(summaries_dir, exist_ok=True)
    
    out_path = os.path.join(summaries_dir, "book_collections_summaries.json")
    
    # Load already processed books
    processed = load_processed_books(out_path)
    print(f"📋 Found {len(processed)} already processed book collections")
    
    # Fetch the Book page
    book_page_title = "Book"
    print(f"📄 Fetching {book_page_title} page...")
    
    try:
        book_page_html = mw.page_html(book_page_title)
    except MediaWikiError as e:
        print(f"❌ Error: Failed to fetch {book_page_title} page: {e}")
        return
    
    if not book_page_html:
        print(f"❌ Error: Could not fetch {book_page_title} page")
        return
    
    # Extract book collection links from the table
    book_titles = extract_book_links_from_table(book_page_html, mw.base_url)
    print(f"🔗 Extracted {len(book_titles)} book collection links")
    
    # Filter out already processed books
    remaining = [title for title in book_titles if title not in processed]
    skipped = len(book_titles) - len(remaining)
    
    if skipped > 0:
        print(f"⏭️  Skipping {skipped} already processed books")
    
    # Load existing data if file exists (for resuming interrupted runs)
    book_data: List[Dict] = []
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    book_data = existing_data
                    existing_titles = {item.get("title") for item in book_data}
                    # Filter out already processed titles
                    remaining = [t for t in remaining if t not in existing_titles]
                    print(f"📂 Resuming: Found {len(book_data)} existing entries, {len(remaining)} remaining")
        except (json.JSONDecodeError, IOError):
            print(f"⚠️  Could not load existing file, starting fresh")
    
    if not remaining:
        print(f"✅ All {len(book_titles)} books already processed → {out_path}")
        return
    
    # Process each book
    new_count = 0
    save_interval = 10  # Save every N books
    
    for book_title in tqdm(remaining, desc="Processing book collections", unit="book"):
        # Extract Vol sections using MediaWiki API
        try:
            volumes = extract_vol_sections(mw, book_title)
        except MediaWikiError as e:
            print(f"⚠️  Warning: Failed to fetch {book_title} after retries: {e}")
            volumes = []
        
        # Combine all volumes' content into a single text field
        text_parts = []
        for vol in volumes:
            vol_name = vol.get("volume", "")
            vol_content = vol.get("content", "")
            if vol_content:
                if vol_name:
                    text_parts.append(f"{vol_name}\n\n{vol_content}")
                else:
                    text_parts.append(vol_content)
        
        text = "\n\n".join(text_parts) if text_parts else ""
        
        if not text.strip():
            print(f"⚠️  Warning: No Vol sections found in {book_title}")
            # Still save the record with empty text
            text = ""
        
        # Create record matching summaries format (but with "text" instead of "summary")
        rec = {
            "title": book_title,
            "url": mw.canonical_url(mw.base_url, book_title),
            "text": text,
        }
        
        book_data.append(rec)
        new_count += 1
        
        # Save incrementally every N books
        if len(book_data) % save_interval == 0:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(book_data, f, ensure_ascii=False, indent=2)
    
    # Final save
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(book_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Processed {new_count} new book collections ({skipped} skipped, {len(book_titles)} total) → {out_path}")


if __name__ == "__main__":
    main()
