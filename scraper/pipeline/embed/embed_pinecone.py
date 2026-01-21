# pipeline/embed/embed_pinecone.py
from __future__ import annotations
import os, json
import re
import unicodedata
import hashlib
from typing import Iterable
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm

load_dotenv()
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# Helper to find data directory (check scraper/data first, then project_root/data)
def get_data_dir():
    """Find the data directory, checking scraper/data first, then project_root/data."""
    # Calculate project root (3 levels up from scraper/pipeline/embed/embed_pinecone.py)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    scraper_data = os.path.join(project_root, "scraper", "data")
    root_data = os.path.join(project_root, "data")
    if os.path.exists(scraper_data):
        return scraper_data
    elif os.path.exists(root_data):
        return root_data
    else:
        # Default to scraper/data if neither exists (will be created)
        return scraper_data

def sanitize_vector_id(vector_id: str) -> str:
    """
    Sanitize vector ID to be ASCII-only for Pinecone compatibility.
    IDs from make_jsonl.py are already <= 512 chars, so we only need Unicode/ASCII normalization.
    
    Args:
        vector_id: Original vector ID (may contain non-ASCII characters)
    
    Returns:
        ASCII-safe vector ID
    """
    # Normalize unicode characters (e.g., convert accented chars to base: "é" → "e")
    normalized = unicodedata.normalize('NFKD', vector_id)
    
    # Convert to ASCII, ignoring non-ASCII characters
    ascii_id = normalized.encode('ascii', 'ignore').decode('ascii')
    
    # Remove any remaining problematic characters (keep alphanumeric, colon, underscore, dash, dot)
    ascii_id = re.sub(r'[^a-zA-Z0-9:_\-.]', '_', ascii_id)
    
    # Collapse multiple underscores
    ascii_id = re.sub(r'_+', '_', ascii_id)
    
    # Remove leading/trailing underscores
    ascii_id = ascii_id.strip('_')
    
    # IDs should already be <= 512 from make_jsonl.py, but add safety check
    MAX_LENGTH = 512
    if len(ascii_id) > MAX_LENGTH:
        # Fallback: truncate and hash (shouldn't happen, but safety net)
        full_hash = hashlib.md5(vector_id.encode('utf-8')).hexdigest()[:12]
        truncate_to = MAX_LENGTH - 13
        ascii_id = ascii_id[:truncate_to] + '_' + full_hash
    
    return ascii_id

def should_skip_chunk(text: str) -> bool:
    """
    Check if a chunk should be skipped due to low quality.
    Returns True if chunk should be skipped.
    """
    if not text:
        return True
    
    text_stripped = text.strip()
    
    # Skip if too short (less than 30 characters or less than 5 words)
    if len(text_stripped) < 30:
        word_count = len(text_stripped.split())
        if word_count < 5:
            return True
    
    # Skip navigation elements and common non-content patterns
    skip_patterns = [
        "Dialogue",
        "Gallery",
        "Other Languages",
        "Change History",
        "Navigation",
    ]
    
    if text_stripped in skip_patterns:
        return True
    
    return False

def iter_jsonl(path: str):
    """Iterate over JSONL file."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)

def count_jsonl_lines(path: str) -> int:
    """Count lines in JSONL file for progress tracking."""
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f)

def load_processed_ids(progress_file: str) -> set:
    """
    Load processed vector IDs from progress file.
    Sanitizes IDs to handle any legacy non-ASCII entries.
    
    Args:
        progress_file: Path to progress file (one ID per line)
    
    Returns:
        Set of processed vector IDs (all sanitized to ASCII)
    """
    if not os.path.exists(progress_file):
        return set()
    
    try:
        with open(progress_file, "r", encoding="utf-8") as f:
            # Sanitize all IDs when loading (handles legacy entries with non-ASCII)
            return {sanitize_vector_id(line.strip()) for line in f if line.strip()}
    except Exception as e:
        print(f"⚠️  Warning: Could not load progress file {progress_file}: {e}")
        return set()

def save_processed_ids(progress_file: str, vector_ids: list[str]):
    """
    Append processed vector IDs to progress file.
    
    Args:
        progress_file: Path to progress file
        vector_ids: List of vector IDs to save
    """
    if not vector_ids:
        return
    
    try:
        os.makedirs(os.path.dirname(progress_file), exist_ok=True)
        with open(progress_file, "a", encoding="utf-8") as f:
            for vector_id in vector_ids:
                f.write(f"{vector_id}\n")
    except Exception as e:
        print(f"⚠️  Warning: Could not save progress to {progress_file}: {e}")

def embed_corpus_file(
    corpus: str,
    path: str,
    index,
    embeddings,
    processed_ids: set,
    progress_file: str,
    content_type: str = "full"
):
    """
    Embed and upsert a single corpus JSONL file to Pinecone.
    
    Args:
        corpus: Name of the corpus
        path: Path to the JSONL file
        index: Pinecone index object
        embeddings: LangChain embeddings object
        processed_ids: Set of already processed IDs (updated in place)
        progress_file: Path to progress tracking file
        content_type: "full" or "summary" for metadata
    """
    if not os.path.exists(path):
        print(f"⏭️  Skipping {corpus} (file not found)")
        return
    
    total_lines = count_jsonl_lines(path)
    if total_lines == 0:
        print(f"⏭️  Skipping {corpus} (empty file)")
        return
    
    print(f"🔎 Embedding {corpus} ({total_lines} chunks)")
    batch = []
    batch_ids = []
    batch_texts = []
    batch_metadatas = []
    already_processed_count = 0
    filtered_count = 0
    newly_embedded_count = 0
    seen_ids_this_run = set()
    
    for rec in tqdm(iter_jsonl(path), total=total_lines, desc=f"Embedding {corpus}", unit="chunk"):
        try:
            # Sanitize ID to be ASCII-only for Pinecone
            original_sanitized_id = sanitize_vector_id(rec["id"])
            sanitized_id = original_sanitized_id
            
            # If this ID was already seen in this run, append text_hash to make it unique
            if sanitized_id in seen_ids_this_run:
                text_hash = rec.get("text_hash", "")
                if text_hash:
                    sanitized_id = f"{sanitized_id}_{text_hash[:8]}"
                else:
                    text_hash_fallback = hashlib.sha1(rec.get("text", "").encode("utf-8")).hexdigest()[:8]
                    sanitized_id = f"{sanitized_id}_{text_hash_fallback}"
                
                # Handle hash collisions
                collision_count = 0
                while sanitized_id in seen_ids_this_run:
                    collision_count += 1
                    text_hash = rec.get("text_hash", "")
                    if text_hash:
                        sanitized_id = f"{original_sanitized_id}_{text_hash[:12]}_{collision_count}"
                    else:
                        text_hash_fallback = hashlib.sha1(f"{rec.get('text', '')}{collision_count}".encode("utf-8")).hexdigest()[:12]
                        sanitized_id = f"{original_sanitized_id}_{text_hash_fallback}"
            
            seen_ids_this_run.add(sanitized_id)
            
            # Skip if already processed
            if sanitized_id in processed_ids:
                already_processed_count += 1
                continue
            
            # Skip low-quality chunks
            if should_skip_chunk(rec.get("text", "")):
                filtered_count += 1
                continue
            
            # Prepare batch for LangChain
            batch_texts.append(rec["text"])
            metadata = {
                "text": rec["text"],
                "type": rec["type"],
                "title": rec["title"],
                "section": rec["section"],
                "url": rec["source_url"],
                "lang": rec.get("lang", "en"),
                "content_type": content_type,
            }
            # Add characters field for summaries
            if content_type == "summary" and "characters" in rec:
                metadata["characters"] = rec["characters"]
            batch_metadatas.append(metadata)
            batch_ids.append(sanitized_id)
            
            # Process batch when it reaches 100
            if len(batch_texts) >= 100:
                # Generate embeddings using LangChain
                embeds = embeddings.embed_documents(batch_texts)
                
                # Prepare batch for Pinecone
                batch = [
                    (batch_ids[i], embeds[i], batch_metadatas[i])
                    for i in range(len(batch_ids))
                ]
                
                index.upsert(batch)
                save_processed_ids(progress_file, batch_ids)
                processed_ids.update(batch_ids)
                newly_embedded_count += len(batch_ids)
                
                batch = []
                batch_ids = []
                batch_texts = []
                batch_metadatas = []
        except Exception as e:
            print(f"⚠️  Error processing chunk {rec.get('id', 'unknown')}: {e}")
            continue
    
    # Process final batch if any remain
    if batch_texts:
        embeds = embeddings.embed_documents(batch_texts)
        batch = [
            (batch_ids[i], embeds[i], batch_metadatas[i])
            for i in range(len(batch_ids))
        ]
        index.upsert(batch)
        save_processed_ids(progress_file, batch_ids)
        processed_ids.update(batch_ids)
        newly_embedded_count += len(batch_ids)
    
    # Report statistics
    stats_parts = []
    if already_processed_count > 0:
        stats_parts.append(f"{already_processed_count} already processed")
    if newly_embedded_count > 0:
        stats_parts.append(f"{newly_embedded_count} newly embedded")
    if filtered_count > 0:
        stats_parts.append(f"{filtered_count} filtered (low quality)")
    
    if stats_parts:
        print(f"   📊 {', '.join(stats_parts)}")
    print(f"✅ Completed {corpus}")

def main():
    # Initialize Pinecone
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index_name = os.environ.get("PINECONE_INDEX_NAME", "genshin-lore")
    
    # Get embedding dimension based on model
    # text-embedding-3-small: 1536 dimensions
    # text-embedding-3-large: 3072 dimensions
    dimension = 1536 if "small" in EMBED_MODEL.lower() else 3072
    
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print(f"✅ Created new index: {index_name} (dimension: {dimension})")
    
    index = pc.Index(index_name)
    
    # Initialize LangChain embeddings
    embeddings = OpenAIEmbeddings(model=EMBED_MODEL)
    
    # Initialize progress tracking
    data_dir = get_data_dir()
    progress_file = os.path.join(data_dir, "interim", "embedding_progress.txt")
    processed_ids = load_processed_ids(progress_file)
    if processed_ids:
        print(f"📂 Resuming: Found {len(processed_ids)} already-processed vectors")
    else:
        print("🆕 Starting fresh embedding run")
    
    # Embed and upsert each corpus file
    jsonl_dir = os.path.join(data_dir, "jsonl")
    # NOTE: Commented out to embed ONLY miscellaneous corpora.
    # for corpus in ["characters", "archon_quests", "story_quests", "world_quests", "books"]:
    #     path = os.path.join(jsonl_dir, f"{corpus}.jsonl")
    #     embed_corpus_file(
    #         corpus=corpus,
    #         path=path,
    #         index=index,
    #         embeddings=embeddings,
    #         processed_ids=processed_ids,
    #         progress_file=progress_file,
    #         content_type="full"
    #     )
    
    # Embed summaries from JSONL files (if they exist)
    # NOTE: Commented out to embed ONLY miscellaneous corpora.
    # print(f"\n{'='*60}")
    # print("Embedding summaries...")
    # print(f"{'='*60}")
    #
    # summary_corpus_list = [
    #     "archon_quests_summaries",
    #     "story_quests_summaries",
    #     "world_quests_summaries",
    # ]
    #
    # for corpus in summary_corpus_list:
    #     path = os.path.join(jsonl_dir, f"{corpus}.jsonl")
    #     embed_corpus_file(
    #         corpus=corpus,
    #         path=path,
    #         index=index,
    #         embeddings=embeddings,
    #         processed_ids=processed_ids,
    #         progress_file=progress_file,
    #         content_type="summary"
    #     )

    # Embed miscellaneous from JSONL files (if they exist)
    print(f"\n{'='*60}")
    print("Embedding miscellaneous...")
    print(f"{'='*60}")

    miscellaneous_corpus_list = [
        "artifact_lore",
        "groups_lore",
        "teyvat_lore",
        "playable_characters",
        "book_collections_summaries"
    ]

    for corpus in miscellaneous_corpus_list:
        path = os.path.join(jsonl_dir, f"{corpus}.jsonl")
        embed_corpus_file(
            corpus=corpus,
            path=path,
            index=index,
            embeddings=embeddings,
            processed_ids=processed_ids,
            progress_file=progress_file,
            content_type="misc"
        )


if __name__ == "__main__":
    main()
