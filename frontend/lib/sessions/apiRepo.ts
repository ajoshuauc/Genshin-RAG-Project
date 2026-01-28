import { Conversation, Message } from "@/features/chat/types";
import { SessionsRepository } from "./repo";

/**
 * API-based implementation of SessionsRepository.
 * STUB: Not implemented yet. This will call the FastAPI backend:
 *   - GET /api/v1/sessions - list sessions
 *   - GET /api/v1/sessions/{session_id} - get session
 *   - POST /api/v1/sessions - create session
 *   - etc.
 */
export class ApiSessionsRepository implements SessionsRepository {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  }

  async listSessions(_userId: string): Promise<Conversation[]> {
    // Future: GET ${this.baseUrl}/api/v1/sessions
    // Headers: X-User-Id: userId
    throw new Error("ApiSessionsRepository.listSessions: Not implemented");
  }

  async getSession(
    _userId: string,
    _sessionId: string
  ): Promise<Conversation | null> {
    // Future: GET ${this.baseUrl}/api/v1/sessions/${sessionId}
    // Headers: X-User-Id: userId
    throw new Error("ApiSessionsRepository.getSession: Not implemented");
  }

  async createSession(_userId: string): Promise<Conversation> {
    // Future: POST ${this.baseUrl}/api/v1/sessions
    // Headers: X-User-Id: userId
    throw new Error("ApiSessionsRepository.createSession: Not implemented");
  }

  async appendMessage(
    _userId: string,
    _sessionId: string,
    _message: Message
  ): Promise<void> {
    // Future: POST ${this.baseUrl}/api/v1/sessions/${sessionId}/messages
    // Headers: X-User-Id: userId
    throw new Error("ApiSessionsRepository.appendMessage: Not implemented");
  }

  async renameSession(
    _userId: string,
    _sessionId: string,
    _title: string
  ): Promise<void> {
    // Future: PATCH ${this.baseUrl}/api/v1/sessions/${sessionId}
    // Headers: X-User-Id: userId
    throw new Error("ApiSessionsRepository.renameSession: Not implemented");
  }

  async deleteSession(_userId: string, _sessionId: string): Promise<void> {
    // Future: DELETE ${this.baseUrl}/api/v1/sessions/${sessionId}
    // Headers: X-User-Id: userId
    throw new Error("ApiSessionsRepository.deleteSession: Not implemented");
  }
}

/**
 * Singleton instance (for future use)
 */
export const apiRepo = new ApiSessionsRepository();
