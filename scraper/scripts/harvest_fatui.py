# scripts/harvest_fatui.py
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


def extract_all_p_tags_text(mw: MediaWikiClient, title: str) -> str:
    """
    Extract all <p> tags from the page using MediaWiki API (not REST).
    Returns the combined text from all paragraphs.
    """
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "formatversion": "2",
    }
    
    try:
        resp = mw._request("GET", mw.api_url, params=params)
        data = resp.json()
        
        parse_data = data.get("parse", {})
        if "missing" in parse_data or "error" in data:
            return ""
        
        html = parse_data.get("text", "")
        if not html:
            return ""
        
        soup = BeautifulSoup(html, "html.parser")
        paragraphs = soup.find_all("p")
        
        content_parts = []
        for p in paragraphs:
            text = p.get_text("\n", strip=True)
            if text:
                content_parts.append(text)
        
        return "\n\n".join(content_parts) if content_parts else ""
        
    except (MediaWikiError, KeyError, ValueError) as e:
        print(f"⚠️  API error for {title}: {e}")
        return ""


def main():
    mw = MediaWikiClient(
        user_agent=os.getenv("USER_AGENT", "genshin-rag/1.0 (contact: ajoshuauc@gmail.com)"),
        base_url=os.getenv("WIKI_BASE", "https://genshin-impact.fandom.com"),
    )
    
    data_dir = get_data_dir()
    misc_dir = os.path.join(data_dir, "interim", "misc")
    os.makedirs(misc_dir, exist_ok=True)
    
    out_path = os.path.join(misc_dir, "fatui.json")
    
    # Page to scrape
    char_name = "Fatui"
    char_url = "https://genshin-impact.fandom.com/wiki/Fatui"
    
    print(f"📄 Fetching {char_name}...")
    
    try:
        text = extract_all_p_tags_text(mw, char_name)
        
        if not text:
            print(f"⚠️  Warning: No content found for {char_name}")
        else:
            print(f"   ✓ Found {len(text)} chars")
        
        output = [{
            "character": char_name,
            "url": char_url,
            "text": text.strip() if text else ""
        }]
        
    except MediaWikiError as e:
        print(f"❌ Error fetching {char_name}: {e}")
        output = [{
            "character": char_name,
            "url": char_url,
            "text": ""
        }]
    
    # Save to JSON
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved to {out_path}")
    print(f"   - {char_name}: {len(output[0]['text'])} chars")


if __name__ == "__main__":
    main()