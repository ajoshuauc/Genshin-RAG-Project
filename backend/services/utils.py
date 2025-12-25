from langchain_core.documents import Document

def format_docs(docs: list[Document]) -> str:
    return "\n\n---\n\n".join([d.page_content for d in docs])