import { Conversation, Message, ChatResponse } from "@/features/chat/types";
import { SessionsRepository } from "./repo";

/**
 * API-based implementation of SessionsRepository.
 * Calls the FastAPI backend for session/message management.
 */
export class ApiSessionsRepository implements SessionsRepository {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  }

  private headers(userId: string): HeadersInit {
    return {
      "Content-Type": "application/json",
      "X-User-Id": userId,
    };
  }

  async listSessions(userId: string): Promise<Conversation[]> {
    const res = await fetch(`${this.baseUrl}/api/v1/sessions`, {
      method: "GET",
      headers: this.headers(userId),
    });

    if (!res.ok) {
      throw new Error(`Failed to list sessions: ${res.status}`);
    }

    const data = await res.json();
    // Transform API response to Conversation[]
    return (data.sessions || []).map(
      (s: { id: string; title: string; created_at: string; updated_at: string }) => ({
        id: s.id,
        title: s.title,
        messages: [], // Messages loaded separately
        createdAt: new Date(s.created_at),
        updatedAt: new Date(s.updated_at),
      })
    );
  }

  async getSession(
    userId: string,
    sessionId: string
  ): Promise<Conversation | null> {
    const res = await fetch(`${this.baseUrl}/api/v1/sessions/${sessionId}`, {
      method: "GET",
      headers: this.headers(userId),
    });

    if (res.status === 404) {
      return null;
    }

    if (!res.ok) {
      throw new Error(`Failed to get session: ${res.status}`);
    }

    const data = await res.json();
    return {
      id: data.session_id,
      title: data.title,
      messages: (data.messages || []).map(
        (m: { id: string; role: "user" | "assistant"; content: string; created_at: string }) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          createdAt: new Date(m.created_at),
        })
      ),
      createdAt: new Date(), // Not returned by API, use now
      updatedAt: new Date(),
    };
  }

  async createSession(_userId: string): Promise<Conversation> {
    // Sessions are created implicitly when first message is sent
    // This creates a local placeholder that will be persisted on first message
    const now = new Date();
    return {
      id: crypto.randomUUID(),
      title: "New Conversation",
      messages: [],
      createdAt: now,
      updatedAt: now,
    };
  }

  /**
   * Send a chat message and get the assistant response.
   * The backend handles message persistence.
   */
  async sendChatMessage(
    userId: string,
    sessionId: string,
    message: string
  ): Promise<ChatResponse> {
    const res = await fetch(`${this.baseUrl}/api/v1/chat`, {
      method: "POST",
      headers: this.headers(userId),
      body: JSON.stringify({
        session_id: sessionId,
        message: message,
      }),
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Chat request failed: ${res.status} - ${errorText}`);
    }

    return await res.json();
  }

  async appendMessage(
    _userId: string,
    _sessionId: string,
    _message: Message
  ): Promise<void> {
    // Messages are appended via sendChatMessage, not separately
    // This is a no-op since the backend handles persistence
  }

  async renameSession(
    _userId: string,
    _sessionId: string,
    _title: string
  ): Promise<void> {
    // Not implemented yet - would need a PATCH endpoint
    console.warn("renameSession: Not implemented on backend yet");
  }

  async deleteSession(_userId: string, _sessionId: string): Promise<void> {
    // Not implemented yet - would need a DELETE endpoint
    console.warn("deleteSession: Not implemented on backend yet");
  }
}

/**
 * Singleton instance
 */
export const apiRepo = new ApiSessionsRepository();
