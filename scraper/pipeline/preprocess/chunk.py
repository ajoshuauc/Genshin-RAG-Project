# pipeline/preprocess/chunk.py
import re
from typing import List

def split_by_sections(md_text: str) -> List[tuple[str,str]]:
    parts = re.split(r"\n## ", md_text)
    out = []
    for part in parts:
        if not part.strip(): 
            continue
        if "\n" in part:
            sec, body = part.split("\n", 1)
        else:
            sec, body = "Overview", part
        out.append((sec.strip(), body.strip()))
    return out

def sliding_window_chunks(text: str, size=1100, overlap=180) -> List[str]:
    chunks, i, n = [], 0, len(text)
    while i < n:
        j = min(n, i + size)
        chunks.append(text[i:j])
        if j == n: break
        i = max(0, j - overlap)
    return chunks
