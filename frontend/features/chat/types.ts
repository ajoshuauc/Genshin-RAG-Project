export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: Date;
}

export interface Conversation {
  id: string; // This is the session_id (UUID) - unified with backend
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatResponse {
  response: string;
  sources?: Array<Record<string, unknown>>;
}
