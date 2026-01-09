# scripts/harvest_character_profiles.py
from __future__ import annotations
import os
import json
import sys
from typing import Set, List, Dict, Optional
from urllib.parse import unquote
from bs4 import BeautifulSoup

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm is not available
    def tqdm(iterable, *args, **kwargs):
        return iterable

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


def extract_character_links_from_table(html: str, base_url: str) -> Set[str]:
    """
    Extract character page titles from the Character/List page's table.
    Looks for the table with class "fandom-table article-table sortable alternating-colors-table jquery-tablesorter"
    and extracts links from the Name column.
    Returns a set of page titles (normalized).
    """
    soup = BeautifulSoup(html, "html.parser")
    titles = set()
    
    # Find the table with the specified class
    def has_table_classes(classes):
        if not classes:
            return False
        class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
        return ("fandom-table" in class_str and 
                "article-table" in class_str and 
                "sortable" in class_str and
                "alternating-colors-table" in class_str)
    
    table = soup.find("table", class_=has_table_classes)
    if not table:
        print("⚠️  Warning: Could not find fandom-table article-table sortable alternating-colors-table table")
        return titles
    
    # Find all rows in tbody
    tbody = table.find("tbody")
    if not tbody:
        print("⚠️  Warning: Could not find tbody in table")
        return titles
    
    rows = tbody.find_all("tr")
    print(f"🔍 Found {len(rows)} rows in character list table")
    
    for row in rows:
        # The Name column is typically the second column (index 1)
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        
        # Look for links in the Name column (second cell)
        name_cell = cells[1]
        link = name_cell.find("a", href=True)
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


def extract_profile_text(mw: MediaWikiClient, character_title: str) -> str:
    """
    Extract all text from <p> tags on the character profile page.
    The profile page URL is constructed by appending "/Profile" to the character title.
    Returns the combined text from all <p> tags.
    """
    # Construct profile page title
    profile_title = f"{character_title}/Profile"
    
    # Get the full page HTML
    try:
        profile_html = mw.page_html(profile_title)
    except MediaWikiError as e:
        print(f"⚠️  Warning: Failed to fetch {profile_title}: {e}")
        return ""
    
    if not profile_html:
        print(f"⚠️  Warning: Could not fetch {profile_title}")
        return ""
    
    # Parse HTML and extract text from all <p> tags
    soup = BeautifulSoup(profile_html, "html.parser")
    paragraphs = soup.find_all("p")
    
    # Extract text from all <p> tags
    content_parts = []
    for p in paragraphs:
        text = p.get_text("\n", strip=True)
        if text:
            content_parts.append(text)
    
    content = "\n\n".join(content_parts) if content_parts else ""
    return content.strip()


def load_processed_characters(out_path: str) -> Set[str]:
    """Load character names that have already been processed from the JSON file."""
    processed = set()
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for rec in data:
                        if "character" in rec:
                            processed.add(rec["character"])
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
    
    out_path = os.path.join(summaries_dir, "playable_characters.json")
    
    # Load already processed characters
    processed = load_processed_characters(out_path)
    print(f"📋 Found {len(processed)} already processed characters")
    
    # Fetch the Character/List page
    character_list_title = "Character/List"
    print(f"📄 Fetching {character_list_title} page...")
    
    try:
        character_list_html = mw.page_html(character_list_title)
    except MediaWikiError as e:
        print(f"❌ Error: Failed to fetch {character_list_title} page: {e}")
        return
    
    if not character_list_html:
        print(f"❌ Error: Could not fetch {character_list_title} page")
        return
    
    # Extract character links from the table
    character_titles = extract_character_links_from_table(character_list_html, mw.base_url)
    print(f"🔗 Extracted {len(character_titles)} character links")
    
    # Filter out already processed characters
    remaining = [title for title in character_titles if title not in processed]
    skipped = len(character_titles) - len(remaining)
    
    if skipped > 0:
        print(f"⏭️  Skipping {skipped} already processed characters")
    
    # Load existing data if file exists (for resuming interrupted runs)
    character_data: List[Dict] = []
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    character_data = existing_data
                    existing_characters = {item.get("character") for item in character_data}
                    # Filter out already processed characters
                    remaining = [t for t in remaining if t not in existing_characters]
                    print(f"📂 Resuming: Found {len(character_data)} existing entries, {len(remaining)} remaining")
        except (json.JSONDecodeError, IOError):
            print(f"⚠️  Could not load existing file, starting fresh")
    
    if not remaining:
        print(f"✅ All {len(character_titles)} characters already processed → {out_path}")
        return
    
    # Process each character
    new_count = 0
    save_interval = 10  # Save every N characters
    
    for character_title in tqdm(remaining, desc="Processing character profiles", unit="character"):
        # Extract text from profile page
        try:
            text = extract_profile_text(mw, character_title)
        except MediaWikiError as e:
            print(f"⚠️  Warning: Failed to fetch {character_title}/Profile after retries: {e}")
            text = ""
        
        if not text.strip():
            print(f"⚠️  Warning: No text found in {character_title}/Profile")
            # Still save the record with empty text
            text = ""
        
        # Create record with "character" field instead of "title"
        rec = {
            "character": character_title,
            "url": mw.canonical_url(mw.base_url, f"{character_title}/Profile"),
            "text": text,
        }
        
        character_data.append(rec)
        new_count += 1
        
        # Save incrementally every N characters
        if len(character_data) % save_interval == 0:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(character_data, f, ensure_ascii=False, indent=2)
    
    # Final save
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(character_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Processed {new_count} new characters ({skipped} skipped, {len(character_titles)} total) → {out_path}")


if __name__ == "__main__":
    main()
