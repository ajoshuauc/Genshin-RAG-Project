# scripts/extract_summaries.py
from __future__ import annotations
import os
import json
from typing import Dict, List, Optional, Set
from urllib.parse import unquote
from tqdm import tqdm
from bs4 import BeautifulSoup, Tag

# Add project root to Python path
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scraper.pipeline.harvest.mediawiki import MediaWikiClient

# Helper to find data directory (check scraper/data first, then project_root/data)
def get_data_dir():
    """Find the data directory, checking scraper/data first, then project_root/data."""
    scraper_data = os.path.join(project_root, "scraper", "data")
    root_data = os.path.join(project_root, "data")
    if os.path.exists(scraper_data):
        return scraper_data
    elif os.path.exists(root_data):
        return root_data
    else:
        # Default to scraper/data if neither exists (will be created)
        return scraper_data

# The three list pages to process
LIST_PAGES = {
    "story_quests": "Story_Quest/List",
    "archon_quests": "Archon_Quest",
    "world_quests": "World_Quest/List",
}


def extract_quest_links_from_html(html: str, base_url: str) -> Set[str]:
    """
    Extract quest page titles from a quest list page HTML.
    Looks for links in the main content area that point to quest pages.
    Specifically targets links inside <ul> lists for Story and World Quests.
    Returns a set of page titles (normalized).
    """
    soup = BeautifulSoup(html, "html.parser")
    titles = set()
    
    # Find all links in the main content area
    # Handle multiple CSS classes (e.g., "mw-content-ltr mw-parser-output")
    content_area = (soup.find("div", class_="mw-parser-output") or 
                    soup.find("div", class_=lambda x: bool(x and ("mw-parser-output" in (x if isinstance(x, str) else " ".join(x) if isinstance(x, list) else str(x))))) or
                    soup.find("div", id="content"))
    if not content_area:
        # If no content area found, try searching the entire document
        print("⚠️  Warning: No mw-parser-output or content div found, searching entire document")
        content_area = soup
    
    # First, try to find links specifically in <ul> lists (for Story and World Quests)
    ul_lists = content_area.find_all("ul")
    print(f"🔍 Found {len(ul_lists)} <ul> lists in content area")
    
    links_from_lists = []
    for i, ul in enumerate(ul_lists):
        list_links = ul.find_all("a", href=True)
        if list_links:
            links_from_lists.extend(list_links)
            # Show first few hrefs as examples
            if i < 3:
                sample_hrefs = [(link.get("href") or "")[:60] for link in list_links[:3]]
                print(f"  List {i+1}: Found {len(list_links)} links, samples: {sample_hrefs}")
    
    print(f"🔍 Found {len(links_from_lists)} total links in <ul> lists")
    
    # Also get all other links (fallback)
    all_links = content_area.find_all("a", href=True)
    print(f"🔍 Found {len(all_links)} total links in content area (including lists)")
    
    # Use links from lists if available, otherwise use all links
    links_to_process = links_from_lists if links_from_lists else all_links
    print(f"📋 Processing {len(links_to_process)} links")
    
    skipped_reasons = {
        "no_wiki_path": [],
        "special_page": [],
        "empty_title": [],
        "skip_pattern": [],
        "list_page": [],
        "too_short": [],
        "valid": []
    }
    
    for link in links_to_process:
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
            if len(skipped_reasons["no_wiki_path"]) < 3:
                skipped_reasons["no_wiki_path"].append(href[:60])
            continue
        
        # Skip external links, anchors, and special pages
        if (wiki_path.startswith("/wiki/File:") or 
            wiki_path.startswith("/wiki/Category:") or 
            wiki_path.startswith("/wiki/Template:") or
            wiki_path.startswith("/wiki/User:") or
            wiki_path.startswith("/wiki/Help:") or
            wiki_path.startswith("/wiki/Special:") or
            wiki_path.startswith("/wiki/MediaWiki:")):
            if len(skipped_reasons["special_page"]) < 3:
                skipped_reasons["special_page"].append(wiki_path[:60])
            continue
        
        # Extract page title from href - also remove query parameters
        title_part = wiki_path.replace("/wiki/", "").split("#")[0].split("?")[0]  # Remove anchor fragments and query params
        if not title_part:
            if len(skipped_reasons["empty_title"]) < 3:
                skipped_reasons["empty_title"].append(wiki_path[:60])
            continue
        
        # URL decode and normalize
        title = unquote(title_part).replace("_", " ")
        
        # Skip empty titles
        if not title or not title.strip():
            if len(skipped_reasons["empty_title"]) < 3:
                skipped_reasons["empty_title"].append(title_part[:60])
            continue
        
        # Skip the list page itself and common non-quest pages
        # But be more careful - only skip if it's exactly the list page or contains these patterns
        skip_patterns = ["category:", "file:", "template:", "user:", "help:", "special:", "mediawiki:"]
        matched_patterns = [s for s in skip_patterns if s in title.lower()]
        if matched_patterns:
            if len(skipped_reasons["skip_pattern"]) < 5:
                skipped_reasons["skip_pattern"].append(f"{title[:50]} (matched: {matched_patterns})")
            continue
        
        # Skip if it's the list page title itself (more flexible matching)
        title_lower = title.lower().strip()
        if title_lower in ["story quest/list", "world quest/list", "archon quest", "story quest", "world quest"]:
            if len(skipped_reasons["list_page"]) < 3:
                skipped_reasons["list_page"].append(title[:60])
            continue
        
        # Skip very short titles (likely not quest names)
        if len(title.strip()) < 3:
            if len(skipped_reasons["too_short"]) < 3:
                skipped_reasons["too_short"].append(title[:60])
            continue
        
        # MediaWiki title normalization: first letter uppercase
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
            titles.add(title)
            if len(skipped_reasons["valid"]) < 5:
                skipped_reasons["valid"].append(title)
    
    print(f"✅ Extracted {len(titles)} quest titles after filtering")
    print(f"   Skipped breakdown:")
    print(f"     - No wiki path: {len(skipped_reasons['no_wiki_path'])}")
    if skipped_reasons['no_wiki_path']:
        print(f"       Examples: {skipped_reasons['no_wiki_path']}")
    print(f"     - Special pages: {len(skipped_reasons['special_page'])}")
    if skipped_reasons['special_page']:
        print(f"       Examples: {skipped_reasons['special_page']}")
    print(f"     - Empty title: {len(skipped_reasons['empty_title'])}")
    if skipped_reasons['empty_title']:
        print(f"       Examples: {skipped_reasons['empty_title']}")
    print(f"     - Skip pattern: {len(skipped_reasons['skip_pattern'])}")
    if skipped_reasons['skip_pattern']:
        print(f"       Examples: {skipped_reasons['skip_pattern'][:3]}")
    print(f"     - List page: {len(skipped_reasons['list_page'])}")
    if skipped_reasons['list_page']:
        print(f"       Examples: {skipped_reasons['list_page']}")
    print(f"     - Too short: {len(skipped_reasons['too_short'])}")
    if skipped_reasons['too_short']:
        print(f"       Examples: {skipped_reasons['too_short']}")
    print(f"     - Valid: {len(skipped_reasons['valid'])}")
    if skipped_reasons['valid']:
        print(f"       Examples: {skipped_reasons['valid']}")
    
    if titles:
        # Show first few titles as sample
        sample_titles = list(titles)[:5]
        print(f"   Sample titles: {', '.join(sample_titles)}")
    return titles


def extract_quest_links_from_section(section_element, base_url: str) -> Set[str]:
    """
    Extract quest links from a specific HTML section element.
    Used for targeting specific sections like "List of Archon Quests".
    """
    titles = set()
    if not section_element:
        print("⚠️  Section element is None or empty")
        return titles
    
    all_links = section_element.find_all("a", href=True)
    print(f"🔍 Found {len(all_links)} links in section")
    
    for link in all_links:
        href_attr = link.get("href")
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
        
        title_part = wiki_path.replace("/wiki/", "").split("#")[0]
        if not title_part:
            continue
        
        title = unquote(title_part).replace("_", " ")
        skip_patterns = ["/list", "/list/", "category:", "file:", "template:", "user:", "help:", "special:", "mediawiki:"]
        if title and not any(skip in title.lower() for skip in skip_patterns):
            # Skip very short titles
            if len(title.strip()) >= 3:
                title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
                titles.add(title)
    
    print(f"✅ Extracted {len(titles)} quest titles from section")
    return titles


def extract_summary_section(mw: MediaWikiClient, title: str) -> Optional[str]:
    """
    Extract the Summary section from a quest page using MediaWiki API.
    More reliable than parsing HTML. Uses API to get sections and extract summary text.
    Returns None if no Summary section is found.
    """
    # Get all sections via API
    sections = mw.page_sections_via_api(title)
    if not sections:
        return None
    
    # Find Summary section (case-insensitive)
    summary_keywords = ("summary", "synopsis", "plot", "overview", "description", "quest description")
    summary_index = None
    
    for section_name, section_idx in sections.items():
        section_name_lower = section_name.lower()
        if any(keyword in section_name_lower for keyword in summary_keywords):
            summary_index = section_idx
            break
    
    if not summary_index:
        return None
    
    # Get the summary section text via API
    summary_text = mw.page_section_text_via_api(title, summary_index)
    return summary_text


def extract_characters_section(mw: MediaWikiClient, title: str) -> Optional[str]:
    """
    Extract the Characters section from a quest page using MediaWiki API.
    More reliable than parsing HTML. Uses API to get sections and extract characters text.
    Returns None if no Characters section is found.
    """
    # Get all sections via API
    sections = mw.page_sections_via_api(title)
    if not sections:
        return None
    
    # Find Characters section (case-insensitive)
    character_keywords = ("characters", "character", "cast", "characters involved", "characters in quest")
    characters_index = None
    
    for section_name, section_idx in sections.items():
        section_name_lower = section_name.lower()
        if any(keyword in section_name_lower for keyword in character_keywords):
            characters_index = section_idx
            break
    
    if not characters_index:
        return None
    
    # Get the characters section text via API
    characters_text = mw.page_section_text_via_api(title, characters_index)
    return characters_text


def extract_summaries(mw: Optional[MediaWikiClient] = None):
    """
    Extract summaries and characters from quest pages.
    
    Args:
        mw: Optional MediaWikiClient instance. If None, creates a new one.
    """
    if mw is None:
        mw = MediaWikiClient(
            user_agent=os.getenv("USER_AGENT", "genshin-rag/1.0 (contact: ajoshuauc@gmail.com)"),
            base_url=os.getenv("WIKI_BASE", "https://genshin-impact.fandom.com"),
        )
    
    # Create summaries directory
    data_dir = get_data_dir()
    summaries_dir = os.path.join(data_dir, "interim", "summaries")
    os.makedirs(summaries_dir, exist_ok=True)
    
    for quest_type, list_page_title in LIST_PAGES.items():
        print(f"\n{'='*60}")
        print(f"Processing {quest_type}: {list_page_title}")
        print(f"{'='*60}")
        
        # Fetch the list page
        print(f"📄 Fetching list page: {list_page_title}")
        list_page_html = mw.page_html(list_page_title)
        if not list_page_html:
            print(f"⚠️  Could not fetch list page: {list_page_title}")
            continue
        
        # For Archon Quest, try to find the "List of Archon Quests" section
        if quest_type == "archon_quests":
            soup = BeautifulSoup(list_page_html, "html.parser")
            content_area = soup.find("div", class_="mw-parser-output") or soup.find("div", id="content")
            
            if content_area:
                # Look for h2 or h3 with "List of Archon Quests" text
                headings = content_area.find_all(["h2", "h3"])
                print(f"🔍 Found {len(headings)} h2/h3 headings in Archon Quest page")
                list_section_found = False
                
                for heading in headings:
                    # Check for mw-headline span first
                    headline_span = heading.find("span", class_="mw-headline")
                    if headline_span:
                        heading_text = headline_span.get_text(strip=True).lower()
                    else:
                        heading_text = heading.get_text(strip=True).lower()
                    
                    print(f"  Checking heading: '{heading_text[:50]}...'")
                    
                    if "list of archon quests" in heading_text:
                        print(f"✅ Found 'List of Archon Quests' section")
                        # Extract all links from the section between this heading and the next
                        # Get all elements after this heading until next h2/h3
                        section_container = soup.new_tag("div")
                        current = heading.next_sibling
                        elements_collected = 0
                        
                        while current is not None:
                            if isinstance(current, Tag):
                                if current.name in ["h2", "h3"]:
                                    break
                                section_container.append(current)
                                elements_collected += 1
                            current = current.next_sibling
                        
                        print(f"  Collected {elements_collected} elements from section")
                        
                        if section_container:
                            extracted_links = extract_quest_links_from_section(section_container, mw.base_url)
                            if extracted_links:
                                quest_titles = extracted_links
                                list_section_found = True
                                print(f"🔗 Found {len(quest_titles)} quest links from List of Archon Quests section")
                                break
                
                # If section-specific extraction didn't work, fall back to full page
                if not list_section_found:
                    print("⚠️  Section-specific extraction failed, falling back to full page")
                    quest_titles = extract_quest_links_from_html(list_page_html, mw.base_url)
                    print(f"🔗 Found {len(quest_titles)} quest links (fallback to full page)")
            else:
                # Fall back to full page extraction
                print("⚠️  No content area found, using full page extraction")
                quest_titles = extract_quest_links_from_html(list_page_html, mw.base_url)
                print(f"🔗 Found {len(quest_titles)} quest links")
        else:
            # Extract all quest links from the list page (for Story and World Quests)
            quest_titles = extract_quest_links_from_html(list_page_html, mw.base_url)
            print(f"🔗 Found {len(quest_titles)} quest links")
        
        if not quest_titles:
            print(f"⚠️  No quest links found in {list_page_title}")
            continue
        
        # Process each quest page and extract summaries and characters
        summaries_data: List[Dict] = []
        skipped_count = 0
        output_file = os.path.join(summaries_dir, f"{quest_type}_summaries.json")
        
        # Load existing summaries if file exists (for resuming interrupted runs)
        if os.path.exists(output_file):
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        summaries_data = existing_data
                        existing_titles = {item.get("title") for item in summaries_data}
                        # Filter out already processed titles
                        quest_titles = {t for t in quest_titles if t not in existing_titles}
                        print(f"📂 Resuming: Found {len(summaries_data)} existing summaries, {len(quest_titles)} remaining")
            except (json.JSONDecodeError, IOError):
                print(f"⚠️  Could not load existing file, starting fresh")
        
        save_interval = 10  # Save every 10 summaries
        
        for title in tqdm(quest_titles, desc=f"Extracting summaries and characters from {quest_type}"):
            # Extract summary section via API (no need to fetch HTML separately)
            summary = extract_summary_section(mw, title)
            # Also extract characters section from the same page
            characters = extract_characters_section(mw, title)
            
            if summary:
                quest_data = {
                    "title": title,
                    "url": mw.canonical_url(mw.base_url, title),
                    "summary": summary,
                }
                # Add characters if found (optional field)
                if characters:
                    quest_data["characters"] = characters
                
                summaries_data.append(quest_data)
                
                # Save incrementally every N summaries
                if len(summaries_data) % save_interval == 0:
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(summaries_data, f, ensure_ascii=False, indent=2)
            else:
                skipped_count += 1
        
        # Final save
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(summaries_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Saved {len(summaries_data)} summaries to {output_file}")
        print(f"⏭️  Skipped {skipped_count} pages (no summary found or page not found)")
    
    print(f"\n{'='*60}")
    print("✅ All summaries and characters extracted!")
    print(f"{'='*60}")


def main():
    """Main entry point for running the script standalone."""
    extract_summaries()


if __name__ == "__main__":
    main()

