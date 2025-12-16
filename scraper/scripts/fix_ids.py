# scripts/fix_ids.py
"""
Script to:
1. Add unique IDs to summary JSON files (they don't have IDs)
2. Fix duplicate IDs in JSONL files by making them unique
"""
from __future__ import annotations
import os
import json
import sys
import hashlib
from collections import defaultdict
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

SRC_DIR = "data/interim"
SUMMARIES_DIR = os.path.join(SRC_DIR, "summaries")
JSONL_DIR = "data/jsonl"


def sanitize_title(title: str) -> str:
    """Convert title to ID-safe format."""
    return title.lower().replace(' ', '_').replace('/', '_').replace('\\', '_').replace('"', '')


def add_ids_to_summaries():
    """Add unique IDs to summary JSON files."""
    if not os.path.exists(SUMMARIES_DIR):
        print(f"❌ Summaries directory not found: {SUMMARIES_DIR}")
        return
    
    summary_files = [f for f in os.listdir(SUMMARIES_DIR) if f.endswith("_summaries.json")]
    
    if not summary_files:
        print(f"❌ No summary JSON files found in {SUMMARIES_DIR}")
        return
    
    print("\n" + "=" * 60)
    print("Adding IDs to Summary JSON Files")
    print("=" * 60)
    
    for fname in summary_files:
        corpus = fname.replace("_summaries.json", "")
        src_path = os.path.join(SUMMARIES_DIR, fname)
        
        print(f"\n📝 Processing {fname}...")
        
        with open(src_path, "r", encoding="utf-8") as f:
            summaries = json.load(f)
        
        updated_count = 0
        for rec in summaries:
            # Skip if ID already exists
            if "id" in rec:
                continue
            
            # Generate ID matching the format from make_jsonl.py
            title_safe = sanitize_title(rec["title"])
            rec["id"] = f"fandom:{corpus}_summaries:{title_safe}:summary"
            updated_count += 1
        
        if updated_count > 0:
            # Write back to file
            with open(src_path, "w", encoding="utf-8") as f:
                json.dump(summaries, f, ensure_ascii=False, indent=2)
            print(f"  ✅ Added IDs to {updated_count} entries")
        else:
            print(f"  ℹ️  All entries already have IDs")
    
    print(f"\n✅ Finished processing summary files")


def fix_duplicate_ids_in_jsonl():
    """Fix duplicate IDs in JSONL files by making them unique."""
    if not os.path.exists(JSONL_DIR):
        print(f"❌ JSONL directory not found: {JSONL_DIR}")
        return
    
    jsonl_files = [f for f in os.listdir(JSONL_DIR) if f.endswith(".jsonl")]
    
    if not jsonl_files:
        print(f"❌ No JSONL files found in {JSONL_DIR}")
        return
    
    print("\n" + "=" * 60)
    print("Fixing Duplicate IDs in JSONL Files")
    print("=" * 60)
    
    for fname in jsonl_files:
        src_path = os.path.join(JSONL_DIR, fname)
        temp_path = src_path + ".tmp"
        
        print(f"\n📝 Processing {fname}...")
        
        # Track ID usage and duplicates
        id_counts = defaultdict(int)
        records = []
        
        # First pass: read all records and identify duplicates
        with open(src_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    rec = json.loads(line)
                    records.append(rec)
                    old_id = rec.get("id", "")
                    id_counts[old_id] += 1
                except json.JSONDecodeError as e:
                    print(f"  ⚠️  Error parsing line {line_num}: {e}")
                    continue
        
        # Identify duplicates
        duplicates = {id_val: count for id_val, count in id_counts.items() if count > 1}
        
        if not duplicates:
            print(f"  ℹ️  No duplicate IDs found")
            continue
        
        print(f"  🔍 Found {len(duplicates)} duplicate ID(s)")
        
        # Second pass: assign unique IDs
        # Group records by old_id to process duplicates together
        records_by_old_id = defaultdict(list)
        for idx, rec in enumerate(records):
            old_id = rec.get("id", "")
            records_by_old_id[old_id].append((idx, rec))
        
        id_sequences = defaultdict(int)  # Track sequence number for each base ID
        seen_new_ids = set()  # Track all new IDs to ensure uniqueness
        
        for old_id, rec_list in records_by_old_id.items():
            if old_id not in duplicates:
                # Not a duplicate, keep original ID
                seen_new_ids.add(old_id)
                continue
            
            # Process duplicates: assign unique IDs using hash + sequence
            for idx, rec in rec_list:
                text_hash = rec.get("text_hash", "")
                
                # Build candidate ID with hash suffix
                if text_hash:
                    hash_suffix = text_hash[:8]
                    base_candidate = f"{old_id}:{hash_suffix}"
                else:
                    hash_suffix = ""
                    base_candidate = old_id
                
                # Check if base candidate is unique
                if base_candidate not in seen_new_ids:
                    candidate_id = base_candidate
                else:
                    # Need to add sequence number for uniqueness
                    id_sequences[old_id] += 1
                    if hash_suffix:
                        candidate_id = f"{old_id}:{hash_suffix}:seq{id_sequences[old_id]}"
                    else:
                        candidate_id = f"{old_id}:seq{id_sequences[old_id]}"
                
                # Final check: ensure absolute uniqueness
                while candidate_id in seen_new_ids:
                    id_sequences[old_id] += 1
                    if hash_suffix:
                        candidate_id = f"{old_id}:{hash_suffix}:seq{id_sequences[old_id]}"
                    else:
                        candidate_id = f"{old_id}:seq{id_sequences[old_id]}"
                
                seen_new_ids.add(candidate_id)
                rec["id"] = candidate_id
        
        # Write updated records
        updated_count = sum(id_counts[id_val] for id_val in duplicates)
        
        with open(temp_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        
        # Replace original file
        os.replace(temp_path, src_path)
        print(f"  ✅ Fixed {updated_count} duplicate ID(s)")
    
    print(f"\n✅ Finished fixing JSONL files")


def main():
    """Main function."""
    print("=" * 60)
    print("ID Fix Script")
    print("=" * 60)
    
    # Add IDs to summary JSON files
    add_ids_to_summaries()
    
    # Fix duplicate IDs in JSONL files
    fix_duplicate_ids_in_jsonl()
    
    print("\n" + "=" * 60)
    print("✅ All done!")
    print("=" * 60)


if __name__ == "__main__":
    main()

