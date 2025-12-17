# scripts/make_jsonl.py
from __future__ import annotations
import os, json, hashlib
import sys
import re
from typing import Set

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from scraper.pipeline.preprocess.clean_html import html_to_markdownish

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

data_dir = get_data_dir()
SRC_DIR = os.path.join(data_dir, "interim")
SUMMARIES_DIR = os.path.join(SRC_DIR, "summaries")
DST_DIR = os.path.join(data_dir, "jsonl")

# Global set to track all IDs across all files to ensure uniqueness
all_ids: Set[str] = set()

# LangChain text splitter optimized for text-embedding-3-small
# Max tokens: 8191, target ~800 tokens per chunk with overlap
# Rough estimate: 1 token ≈ 4 characters for English
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,  # Target ~800 tokens (3200 chars)
    chunk_overlap=150,  # Overlap ~150 tokens (600 chars)
    length_function=len,  # Character-based (can be upgraded to token-based)
    separators=["\n\n", "\n", ". ", " ", ""],  # Split on paragraphs, lines, sentences, words
    is_separator_regex=False,
)

def create_unique_id(base_id: str) -> str:
    """
    Create a unique ID, appending hash suffix if needed.
    Ensures uniqueness across all JSON files.
    Limits ID length to 512 characters for Pinecone compatibility.
    """
    MAX_LENGTH = 512
    
    # First, truncate base_id if too long (before uniqueness check)
    if len(base_id) > MAX_LENGTH:
        # Create a hash of the full ID for uniqueness (first 12 chars of MD5)
        full_hash = hashlib.md5(base_id.encode('utf-8')).hexdigest()[:12]
        # Truncate to leave room for hash suffix (MAX_LENGTH - 1 for separator - 12 for hash)
        truncate_to = MAX_LENGTH - 13
        base_id = base_id[:truncate_to] + '_' + full_hash
    
    # Now check uniqueness (base_id is guaranteed to be <= 512 at this point)
    if base_id not in all_ids:
        all_ids.add(base_id)
        return base_id
    
    # If collision, append hash suffix
    counter = 0
    while True:
        suffix = hashlib.sha1(f"{base_id}_{counter}".encode("utf-8")).hexdigest()[:8]
        unique_id = f"{base_id}_{suffix}"
        # If adding suffix makes it too long, truncate base_id part more
        if len(unique_id) > MAX_LENGTH:
            # Leave room for suffix: MAX_LENGTH - 1 (underscore) - 8 (suffix)
            truncate_base_to = MAX_LENGTH - 9
            unique_id = f"{base_id[:truncate_base_to]}_{suffix}"
        
        if unique_id not in all_ids:
            all_ids.add(unique_id)
            return unique_id
        counter += 1

def sanitize_title(title: str) -> str:
    """Sanitize title for use in IDs."""
    # Normalize: lowercase, replace spaces/slashes with underscores
    sanitized = title.lower().replace(" ", "_").replace("/", "_")
    # Remove special characters, keep alphanumeric, underscore, dash
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', sanitized)
    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized

def process_ndjson_file(src: str, dst: str, corpus: str):
    """Process NDJSON file with HTML content using LangChain chunking."""
    global all_ids
    
    with open(src, encoding="utf-8") as fin, open(dst, "w", encoding="utf-8") as fout:
        for line_num, line in enumerate(fin, start=1):
            try:
                rec = json.loads(line)
                md = html_to_markdownish(rec["html"])
                
                # Split markdown by sections first (## headers)
                sections = re.split(r'\n## ', md)
                
                for section_idx, section_content in enumerate(sections):
                    if not section_content.strip():
                        continue
                    
                    # Extract section name
                    if "\n" in section_content:
                        section_name, body = section_content.split("\n", 1)
                    else:
                        section_name = "Overview"
                        body = section_content
                    
                    section_name = section_name.strip()
                    body = body.strip()
                    
                    if not body:
                        continue
                    
                    # Use LangChain to chunk the section body
                    chunks = text_splitter.split_text(body)
                    
                    for chunk_idx, chunk in enumerate(chunks):
                        if not chunk.strip():
                            continue
                        
                        # Create base ID
                        title_slug = sanitize_title(rec['title'])
                        section_slug = sanitize_title(section_name)
                        base_id = f"fandom:{corpus}:{title_slug}:{section_slug}:{chunk_idx}"
                        
                        # Ensure uniqueness
                        unique_id = create_unique_id(base_id)
                        
                        out = {
                            "id": unique_id,
                            "type": corpus,
                            "title": rec["title"],
                            "section": section_name,
                            "source_url": rec["url"],
                            "license": "CC BY-SA",
                            "lang": "en",
                            "text": chunk,
                            "text_hash": hashlib.sha1(chunk.encode("utf-8")).hexdigest(),
                        }
                        fout.write(json.dumps(out, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"⚠️  Error processing line {line_num} in {src}: {e}")
                continue

def process_summary_file(src: str, dst: str, corpus: str):
    """Process summary JSON file using LangChain chunking."""
    global all_ids
    
    with open(src, encoding="utf-8") as fin, open(dst, "w", encoding="utf-8") as fout:
        summaries = json.load(fin)
        
        for rec in summaries:
            title = rec["title"]
            url = rec["url"]
            summary_text = rec.get("summary", "")
            
            if not summary_text.strip():
                continue
            
            # Use LangChain to chunk the summary
            chunks = text_splitter.split_text(summary_text)
            
            for chunk_idx, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                
                # Create base ID
                title_slug = sanitize_title(title)
                base_id = f"fandom:{corpus}_summaries:{title_slug}:summary:{chunk_idx}"
                
                # Ensure uniqueness
                unique_id = create_unique_id(base_id)
                
                out = {
                    "id": unique_id,
                    "type": f"{corpus}_summaries",
                    "title": title,
                    "section": "Summary",
                    "source_url": url,
                    "license": "CC BY-SA",
                    "lang": "en",
                    "text": chunk,
                    "text_hash": hashlib.sha1(chunk.encode("utf-8")).hexdigest(),
                }
                fout.write(json.dumps(out, ensure_ascii=False) + "\n")

def main():
    global all_ids
    
    os.makedirs(DST_DIR, exist_ok=True)
    
    # Reset global ID tracker
    all_ids.clear()
    
    # Process NDJSON files
    ndjson_files = []
    for fname in os.listdir(SRC_DIR):
        if fname.endswith(".ndjson"):
            ndjson_files.append(fname)
    
    for fname in sorted(ndjson_files):
        corpus = fname.replace(".ndjson", "")
        src = os.path.join(SRC_DIR, fname)
        dst = os.path.join(DST_DIR, f"{corpus}.jsonl")
        print(f"📝 Processing {corpus}...")
        process_ndjson_file(src, dst, corpus)
        print(f"✅ Wrote {dst} ({len([l for l in open(dst, encoding='utf-8')])} chunks)")
    
    # Process summary JSON files
    if os.path.exists(SUMMARIES_DIR):
        summary_files = []
        for fname in os.listdir(SUMMARIES_DIR):
            if fname.endswith("_summaries.json"):
                summary_files.append(fname)
        
        for fname in sorted(summary_files):
            corpus = fname.replace("_summaries.json", "")
            src = os.path.join(SUMMARIES_DIR, fname)
            dst = os.path.join(DST_DIR, f"{corpus}_summaries.jsonl")
            print(f"📝 Processing {corpus} summaries...")
            process_summary_file(src, dst, corpus)
            print(f"✅ Wrote {dst} ({len([l for l in open(dst, encoding='utf-8')])} chunks)")
    
    print(f"\n✅ Total unique IDs created: {len(all_ids)}")

if __name__ == "__main__":
    main()
