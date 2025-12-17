from typing import Dict
from langchain_community.memory import ConversationSummaryBufferMemory

from backend.core.deps import get_llm
from backend.core.config import config

_memory_by_session: Dict[str, ConversationSummaryBufferMemory] = {}

def get_memory(session_id: str) -> ConversationSummaryBufferMemory:
    if session_id not in _memory_by_session:
        _memory_by_session[session_id] = ConversationSummaryBufferMemory(
            llm=get_llm(),
            max_token_limit=config.MAX_TOKEN_LIMIT,
            return_messages=True,
        )
    return _memory_by_session[session_id]
