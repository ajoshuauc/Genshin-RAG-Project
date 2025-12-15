# pipeline/harvest/run_harvest.py
from __future__ import annotations
import os, json, sys
from typing import Dict, Set
from urllib.parse import unquote
from tqdm import tqdm
from pipeline.harvest.mediawiki import MediaWikiClient, MediaWikiError

# Add project root to path for importing extract_summaries
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

CATEGORIES: Dict[str, str] = {
    "characters": "Category:Characters",
    "archon_quests": "Category:Archon Quests",
    "story_quests": "Category:Story Quests",
    "world_quests": "Category:World Quests",
    "quest_acts": "Category:Quest_Acts",
    "books": "Category:Books",
}

CHARACTER_SUBPAGES = ["Profile", "Voice-Over"]

QUEST_LIST_PAGES = {
    "story_quests": "Story_Quest/List",
    "world_quests": "World_Quest/List",
    "archon_quests": "Archon_Quest",
}

def load_processed_titles(out_path: str) -> Set[str]:
    """Load titles that have already been processed from the NDJSON file."""
    processed = set()
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        processed.add(rec["title"])
                    except (json.JSONDecodeError, KeyError):
                        # Skip malformed lines
                        continue
        except Exception as e:
            print(f"⚠️  Warning: Could not read existing file {out_path}: {e}")
    return processed

def extract_quest_links_from_html(html: str, base_url: str) -> Set[str]:
    """
    Extract quest page titles from a quest list page HTML.
    Looks for links in the main content area that point to quest pages.
    Returns a set of page titles (normalized).
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, "html.parser")
    titles = set()
    
    # Find all links in the main content area
    # Handle multiple CSS classes (e.g., "mw-content-ltr mw-parser-output")
    content_area = (soup.find("div", class_="mw-parser-output") or 
                    soup.find("div", class_=lambda x: bool(x and ("mw-parser-output" in (x if isinstance(x, str) else " ".join(x) if isinstance(x, list) else str(x))))) or
                    soup.find("div", id="content"))
    if not content_area:
        return titles
    
    # Find all <a> tags with href attributes pointing to /wiki/ pages
    for link in content_area.find_all("a", href=True):
        href_attr = link.get("href")
        # Convert to string if it's a list (BeautifulSoup can return lists)
        if isinstance(href_attr, list):
            href = str(href_attr[0]) if href_attr else ""
        else:
            href = str(href_attr) if href_attr else ""
        
        # Handle relative paths (./), absolute (/wiki/...), and full URLs (https://.../wiki/...)
        wiki_path = None
        if href.startswith("./"):
            # Convert relative path to wiki path: ./Page_Name -> /wiki/Page_Name
            wiki_path = "/wiki/" + href[2:]  # Remove "./" prefix
        elif href.startswith("/wiki/"):
            wiki_path = href
        elif base_url in href and "/wiki/" in href:
            # Extract the /wiki/... part from absolute URL
            wiki_path = "/wiki/" + href.split("/wiki/", 1)[1]
        
        if not wiki_path:
            continue
        
        # Skip external links, anchors, and special pages
        if (wiki_path.startswith("/wiki/File:") or 
            wiki_path.startswith("/wiki/Category:") or 
            wiki_path.startswith("/wiki/Template:") or
            wiki_path.startswith("/wiki/User:") or
            wiki_path.startswith("/wiki/Help:") or
            wiki_path.startswith("/wiki/Special:")):
            continue
        
        # Extract page title from href (e.g., "/wiki/One_Giant_Step_for_Alchemy%3F" -> "One Giant Step for Alchemy?")
        title_part = wiki_path.replace("/wiki/", "").split("#")[0]  # Remove anchor fragments
        if not title_part:
            continue
        
        # URL decode and normalize
        title = unquote(title_part).replace("_", " ")
        
        # Skip the list page itself and common non-quest pages
        skip_patterns = ["/list", "/list/", "category:", "file:", "template:", "user:", "help:", "special:"]
        if any(skip in title.lower() for skip in skip_patterns):
            continue
        
        # Skip if it's the list page title itself
        if title.lower() in ["story quest/list", "world quest/list", "archon quest"]:
            continue
        
        # MediaWiki title normalization: first letter uppercase
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
            titles.add(title)
    
    return titles

def main():
    mw = MediaWikiClient(
        user_agent=os.getenv("USER_AGENT", "genshin-rag/1.0 (contact: ajoshuauc@gmail.com)"),
        base_url=os.getenv("WIKI_BASE", "https://genshin-impact.fandom.com"),
    )
    os.makedirs("data/interim", exist_ok=True)

    for key, cat in CATEGORIES.items():
        out_path = f"data/interim/{key}.ndjson"
        
        # Load already processed titles
        processed = load_processed_titles(out_path)
        print(f"📋 {key}: Found {len(processed)} already processed pages")
        
        # Fetch quest list pages if applicable
        list_page_count = 0
        list_page_links = set()
        if key in QUEST_LIST_PAGES:
            list_page_title = QUEST_LIST_PAGES[key]
            list_page_html = None
            
            # Fetch list page if not already processed
            if list_page_title not in processed:
                try:
                    list_page_html = mw.page_html(list_page_title)
                except MediaWikiError as e:
                    print(f"⚠️  Warning: Failed to fetch list page {list_page_title} after retries: {e}")
                    list_page_html = None
                if list_page_html:
                    with open(out_path, "a", encoding="utf-8") as f:
                        rec = {
                            "title": list_page_title,
                            "category": key,
                            "url": mw.canonical_url(mw.base_url, list_page_title),
                            "html": list_page_html,
                        }
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        f.flush()
                    processed.add(list_page_title)
                    list_page_count = 1
                    print(f"📄 {key}: Fetched list page {list_page_title}")
            
            # Extract quest links from list page (for story_quests and world_quests)
            if key in ["story_quests", "world_quests"]:
                # Get HTML if we just fetched it, otherwise fetch it for link extraction
                if list_page_html is None:
                    try:
                        list_page_html = mw.page_html(list_page_title)
                    except MediaWikiError as e:
                        print(f"⚠️  Warning: Failed to fetch list page {list_page_title} for link extraction: {e}")
                        list_page_html = None
                
                if list_page_html:
                    extracted_links = extract_quest_links_from_html(list_page_html, mw.base_url)
                    list_page_links = extracted_links
                    print(f"🔗 {key}: Extracted {len(extracted_links)} quest links from {list_page_title}")
        
        # Get all category members
        members = mw.category_members(cat)
        total = len(members)
        
        # Create a set of titles from category members
        category_titles = {m["title"] for m in members}
        
        # Merge with links extracted from list pages (for story_quests and world_quests)
        if key in ["story_quests", "world_quests"] and list_page_links:
            all_titles = category_titles | list_page_links
            print(f"📊 {key}: Category has {len(category_titles)} pages, list page has {len(list_page_links)} links, {len(all_titles)} unique total")
            
            # Convert to member-like dicts for processing
            all_members = []
            for title in all_titles:
                # Check if it's from category (has pageid) or from list page
                member = next((m for m in members if m["title"] == title), None)
                if member:
                    all_members.append(member)
                else:
                    # Create a dict for list page links
                    all_members.append({"title": title, "pageid": None, "ns": 0})
            
            members = all_members
            total = len(members)
        else:
            all_titles = category_titles
        
        # Filter out already processed members
        remaining = [m for m in members if m["title"] not in processed]
        skipped = total - len(remaining)
        
        if skipped > 0:
            print(f"⏭️  {key}: Skipping {skipped} already processed pages")
        
        if not remaining:
            print(f"✅ {key}: All {total} pages already processed → {out_path}")
            continue
        
        # Append new records
        new_count = list_page_count  # Start with list page count if fetched
        remaining_count = len(remaining)
        with open(out_path, "a", encoding="utf-8") as f:
            for m in tqdm(remaining, desc=f"Processing {key}", total=remaining_count, unit="page"):
                title = m["title"]
                try:
                    html = mw.page_html(title)
                except MediaWikiError as e:
                    print(f"⚠️  Warning: Failed to fetch {title} after retries: {e}")
                    html = None
                if not html:
                    continue
                rec = {
                    "title": title,
                    "category": key,
                    "url": mw.canonical_url(mw.base_url, title),
                    "html": html,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()  # Ensure data is written immediately
                new_count += 1
                
                # Fetch character subpages if applicable
                if key == "characters":
                    for subpage in CHARACTER_SUBPAGES:
                        subpage_title = f"{title}/{subpage}"
                        if subpage_title not in processed:
                            try:
                                subpage_html = mw.page_html(subpage_title)
                            except MediaWikiError as e:
                                print(f"⚠️  Warning: Failed to fetch subpage {subpage_title} after retries: {e}")
                                subpage_html = None
                            if subpage_html:
                                rec = {
                                    "title": subpage_title,
                                    "category": key,
                                    "url": mw.canonical_url(mw.base_url, subpage_title),
                                    "html": subpage_html,
                                }
                                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                                f.flush()
                                processed.add(subpage_title)
                                new_count += 1
        
        print(f"✅ {key}: Processed {new_count} new pages ({skipped} skipped, {total} total) → {out_path}")
    
    # Extract summaries after harvesting quest pages
    print(f"\n{'='*60}")
    print("Extracting quest summaries...")
    print(f"{'='*60}")
    try:
        from scripts.extract_summaries import extract_summaries
        extract_summaries(mw)
    except ImportError as e:
        print(f"⚠️  Warning: Could not import extract_summaries: {e}")
        print("   Skipping summary extraction.")
    except Exception as e:
        print(f"⚠️  Warning: Error during summary extraction: {e}")
        print("   Continuing without summary extraction.")

if __name__ == "__main__":
    main()
