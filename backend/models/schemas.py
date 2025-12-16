from pydantic import BaseModel
from typing import Optional, Any, Dict, List

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    # optional debugging (you can remove this later)
    sources: Optional[List[Dict[str, Any]]] = None

    