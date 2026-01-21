from langchain_core.documents import Document
import hashlib

def format_docs(docs: list[Document]) -> str:
    """
    Format retrieved Documents into a labeled context block.

    Key goals:
    - Preserve source boundaries (title/section/url) to reduce "fact mixing"
    - Provide stable chunk indices ([1], [2], ...) for citation in the answer
    - De-duplicate identical chunks to reduce repetition/noise
    """
    parts: list[str] = []
    seen: set[str] = set()

    for i, d in enumerate(docs, start=1):
        md = d.metadata or {}
        title = (md.get("title") or "").strip() or "(unknown title)"
        section = (md.get("section") or "").strip()
        url = (md.get("url") or "").strip()
        doc_type = (md.get("type") or "").strip()

        content = (d.page_content or "").strip()
        if not content:
            continue

        # Fingerprint for simple deduplication across retrievers/queries
        fp_src = f"{title}\n{section}\n{url}\n{content}".encode("utf-8", errors="ignore")
        fp = hashlib.sha1(fp_src).hexdigest()
        if fp in seen:
            continue
        seen.add(fp)

        header = f"[{i}] {title}"
        if section:
            header += f" — {section}"
        meta_lines: list[str] = []
        if doc_type:
            meta_lines.append(f"TYPE: {doc_type}")
        if url:
            meta_lines.append(f"URL: {url}")

        meta_block = ("\n" + "\n".join(meta_lines)) if meta_lines else ""
        parts.append(f"{header}{meta_block}\n{content}")

    return "\n\n---\n\n".join(parts)