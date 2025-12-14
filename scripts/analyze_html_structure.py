# scripts/analyze_html_structure.py
from __future__ import annotations
import json
from collections import Counter
from bs4 import BeautifulSoup

# Analyze a sample of records
files_to_check = [
    "data/interim/books.ndjson",
    "data/interim/archon_quests.ndjson",
    "data/interim/world_quests.ndjson",
]

all_classes = Counter()
all_tags = Counter()
all_selectors_found = Counter()

# Common elements to check for
check_selectors = [
    "script", "style", ".mw-editsection", ".navigation-box", 
    ".sidebar", ".mw-sidebar", ".reference", ".mw-references-wrap",
    ".dablink", ".hatnote", ".gallery", ".thumb", ".mw-cite-backlink",
    ".catlinks", ".portable-infobox", ".infobox", ".navbox", "table"
]

for filepath in files_to_check:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 5:  # Check first 5 records per file
                    break
                rec = json.loads(line)
                html = rec.get("html", "")
                if not html:
                    continue
                
                soup = BeautifulSoup(html, "html.parser")
                
                # Count all tags
                for tag in soup.find_all():
                    all_tags[tag.name] += 1
                    if tag.get("class"):
                        for cls in tag.get("class", []):
                            all_classes[cls] += 1
                
                # Check for specific selectors
                for selector in check_selectors:
                    if soup.select(selector):
                        all_selectors_found[selector] += len(soup.select(selector))
    except FileNotFoundError:
        print(f"⚠️  {filepath} not found, skipping")
    except Exception as e:
        print(f"⚠️  Error processing {filepath}: {e}")

print("=" * 60)
print("HTML TAGS FOUND (top 20):")
print("=" * 60)
for tag, count in all_tags.most_common(20):
    print(f"  {tag}: {count}")

print("\n" + "=" * 60)
print("CSS CLASSES FOUND (top 30):")
print("=" * 60)
for cls, count in all_classes.most_common(30):
    print(f"  {cls}: {count}")

print("\n" + "=" * 60)
print("SPECIFIC SELECTORS CHECK:")
print("=" * 60)
for selector in check_selectors:
    count = all_selectors_found.get(selector, 0)
    if count > 0:
        print(f"  ✓ {selector}: {count} instances found")
    else:
        print(f"  ✗ {selector}: not found")

