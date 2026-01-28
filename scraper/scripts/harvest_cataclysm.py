# scripts/harvest_cataclysm.py
from __future__ import annotations
import os
import json
import sys
from typing import List, Dict, Optional
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


def get_section_html_via_api(mw: MediaWikiClient, title: str, section_index: str) -> Optional[str]:
    """
    Get a specific section's HTML via MediaWiki API.
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


def extract_all_p_tags(mw: MediaWikiClient, title: str) -> List[Dict[str, str]]:
    """
    Extract all <p> tags from the page, organized by section.
    Returns a list of dicts with 'section' (heading text) and 'content' (text from p tags).
    """
    results = []
    
    # Get all sections via API
    sections = mw.page_sections_via_api(title)
    if not sections:
        # If no sections, try getting the whole page
        html = mw.page_html(title)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            paragraphs = soup.find_all("p")
            content_parts = []
            for p in paragraphs:
                text = p.get_text("\n", strip=True)
                if text:
                    content_parts.append(text)
            if content_parts:
                results.append({
                    "section": "Main",
                    "content": "\n\n".join(content_parts)
                })
        return results
    
    # Process each section
    for section_name, section_idx in sections.items():
        section_html = get_section_html_via_api(mw, title, section_idx)
        if not section_html:
            continue
        
        # Parse HTML and extract text from <p> tags
        soup = BeautifulSoup(section_html, "html.parser")
        paragraphs = soup.find_all("p")
        
        content_parts = []
        for p in paragraphs:
            text = p.get_text("\n", strip=True)
            if text:
                content_parts.append(text)
        
        content = "\n\n".join(content_parts) if content_parts else ""
        
        if content.strip():
            results.append({
                "section": section_name,
                "content": content.strip()
            })
    
    return results


def main():
    mw = MediaWikiClient(
        user_agent=os.getenv("USER_AGENT", "genshin-rag/1.0 (contact: ajoshuauc@gmail.com)"),
        base_url=os.getenv("WIKI_BASE", "https://genshin-impact.fandom.com"),
    )
    
    data_dir = get_data_dir()
    misc_dir = os.path.join(data_dir, "interim", "misc")
    os.makedirs(misc_dir, exist_ok=True)
    
    out_path = os.path.join(misc_dir, "cataclysm_summary.json")
    
    # Page to scrape
    page_title = "Cataclysm"
    page_url = "https://genshin-impact.fandom.com/wiki/Cataclysm"
    
    print(f"📄 Fetching {page_title} page...")
    
    try:
        # Extract all p tags organized by section
        sections_data = extract_all_p_tags(mw, page_title)
        
        if not sections_data:
            print(f"❌ Error: Could not extract content from {page_title}")
            return
        
        print(f"🔍 Found {len(sections_data)} sections with content")
        
        # Build output structure - array of objects, one per section
        page_url = "https://genshin-impact.fandom.com/wiki/Cataclysm"
        output = [
            {
                "title": s["section"],
                "url": page_url,
                "content": s["content"]
            }
            for s in sections_data
        ]
        
        # Save to JSON
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Saved {len(output)} sections to {out_path}")
        
        # Print summary
        for item in output:
            print(f"   - {item['title']}: {len(item['content'])} chars")
            
    except MediaWikiError as e:
        print(f"❌ Error: Failed to fetch {page_title}: {e}")
        return


if __name__ == "__main__":
    main()