from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.retrievers import ContextualCompressionRetriever

from backend.core.deps import get_llm, get_vectorstore
from backend.core.config import config
from backend.services.utils import format_docs
from backend.services.memory import get_memory, persist_memory


def build_query_rewrite_chain():
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template()

