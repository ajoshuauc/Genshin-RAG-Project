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


def extract_other_books_links(html: str, base_url: str) -> Set[str]:
    """
    Extract book page titles from the "Other Books" section on the Book page.
    Finds the h2 heading with "Other Books" text or span with id "Other_Books" and extracts links from the table below it.
    Returns a set of page titles (normalized).
    """
    soup = BeautifulSoup(html, "html.parser")
    titles = set()
    
    # Find the "Other Books" heading - try multiple approaches
    other_books_heading = None
    
    # First, try finding by span id "Other_Books" (case-insensitive)
    other_books_span = soup.find("span", id="Other_Books")
    if not other_books_span:
        # Try case-insensitive search
        for span in soup.find_all("span", id=True):
            if span.get("id", "").lower() == "other_books":
                other_books_span = span
                break
    
    if other_books_span:
        # Find the parent heading (h2 or h3)
        other_books_heading = other_books_span.find_parent(["h2", "h3"])
    
    # If not found, try searching for any span containing "Other Books" text
    if not other_books_heading:
        for span in soup.find_all("span"):
            span_text = span.get_text(strip=True)
            if span_text == "Other Books" or "Other Books" in span_text:
                other_books_heading = span.find_parent(["h2", "h3"])
                if other_books_heading:
                    break
    
    # If still not found, try the mw-headline approach
    if not other_books_heading:
        for heading in soup.find_all(["h2", "h3"]):
            headline = heading.find("span", class_="mw-headline")
            if headline:
                heading_text = headline.get_text(strip=True)
                if "Other Books" in heading_text:
                    other_books_heading = heading
                    break
    
    # If we still don't have a heading but found a span earlier, try to find table from span's parent
    if not other_books_heading and not other_books_span:
        # Try to find the span one more time by text
        for span in soup.find_all("span"):
            span_text = span.get_text(strip=True)
            if span_text == "Other Books":
                other_books_span = span
                # Try to get parent heading one more time
                other_books_heading = span.find_parent(["h2", "h3"])
                if other_books_heading:
                    break
    
    # Last resort: search for all tables and find one that's near "Other Books" text
    fallback_table = None
    if not other_books_heading and not other_books_span:
        # Search for any element containing "Other Books" and find nearby table
        for element in soup.find_all(text=lambda text: text and "Other Books" in text):
            parent = element.parent
            # Look for table in siblings or nearby
            for sibling in parent.find_next_siblings():
                if sibling.name == "table":
                    fallback_table = sibling
                    other_books_heading = parent.find_parent(["h2", "h3"])
                    break
            if fallback_table:
                break
    
    if not other_books_heading and not other_books_span and not fallback_table:
        print("⚠️  Warning: Could not find 'Other Books' heading or span")
        return titles
    
    # Find the table that follows the heading or span
    # If we found a fallback table, use it directly
    if fallback_table:
        table = fallback_table
    else:
        # Look for the next table element after the heading/span
        if other_books_heading:
            current = other_books_heading.find_next_sibling()
        else:
            # If we only have the span, find its parent and then search from there
            parent = other_books_span.find_parent()
            current = parent.find_next_sibling() if parent else other_books_span.find_next_sibling()
        
        table = None
        
        while current:
            if current.name == "table":
                table = current
                break
            # Stop if we hit another h2 heading (next section)
            if current.name in ["h2", "h3"]:
                break
            current = current.find_next_sibling()
    
    if not table:
        print("⚠️  Warning: Could not find table under 'Other Books' section")
        return titles
    
    # Find all rows in tbody
    tbody = table.find("tbody")
    if not tbody:
        print("⚠️  Warning: Could not find tbody in 'Other Books' table")
        return titles
    
    rows = tbody.find_all("tr")
    print(f"🔍 Found {len(rows)} rows in 'Other Books' table")
    
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        
        # The Title column is typically the second column (index 1)
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


def extract_text_section(mw: MediaWikiClient, title: str) -> Optional[str]:
    """
    Extract the Text section from a book page using MediaWiki API.
    More reliable than parsing HTML. Uses API to get sections and extract text content.
    Returns None if no Text section is found.
    """
    # Get all sections via API
    sections = mw.page_sections_via_api(title)
    if not sections:
        return None
    
    # Find Text section (case-insensitive)
    text_keywords = ("text", "book text", "content")
    text_index = None
    
    for section_name, section_idx in sections.items():
        section_name_lower = section_name.lower()
        if any(keyword in section_name_lower for keyword in text_keywords):
            # Prefer exact "Text" match, but accept any containing "text"
            if section_name_lower == "text":
                text_index = section_idx
                break
            elif text_index is None:  # Use first match if no exact match found
                text_index = section_idx
    
    if not text_index:
        return None
    
    # Get the text section content via API
    text_content = mw.page_section_text_via_api(title, text_index)
    return text_content


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
    
    # Extract book collection links from the main table
    book_titles = extract_book_links_from_table(book_page_html, mw.base_url)
    print(f"🔗 Extracted {len(book_titles)} book collection links from main table")
    
    # Extract "Other Books" links
    other_books_titles = extract_other_books_links(book_page_html, mw.base_url)
    print(f"🔗 Extracted {len(other_books_titles)} book links from 'Other Books' section")
    
    # Combine all book titles
    all_book_titles = book_titles | other_books_titles
    print(f"📚 Total unique books: {len(all_book_titles)}")
    
    # Filter out already processed books
    remaining = [title for title in all_book_titles if title not in processed]
    skipped = len(all_book_titles) - len(remaining)
    
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
        print(f"✅ All {len(all_book_titles)} books already processed → {out_path}")
        return
    
    # Process each book
    new_count = 0
    save_interval = 10  # Save every N books
    
    for book_title in tqdm(remaining, desc="Processing books", unit="book"):
        text = ""
        
        # Determine if this is a book collection (has Vol sections) or other book (has Text section)
        # Try Vol sections first (for book collections)
        try:
            volumes = extract_vol_sections(mw, book_title)
            if volumes:
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
            else:
                # If no Vol sections, try Text section (for other books)
                text = extract_text_section(mw, book_title) or ""
                if not text.strip():
                    print(f"⚠️  Warning: No Vol sections or Text section found in {book_title}")
        except MediaWikiError as e:
            print(f"⚠️  Warning: Failed to fetch {book_title} after retries: {e}")
            text = ""
        
        # Create record matching summaries format (but with "text" instead of "summary")
        rec = {
            "title": book_title,
            "url": mw.canonical_url(mw.base_url, book_title),
            "text": text.strip() if text else "",
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
    
    print(f"✅ Processed {new_count} new books ({skipped} skipped, {len(all_book_titles)} total) → {out_path}")


if __name__ == "__main__":
    main()