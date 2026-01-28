import { Conversation, Message } from "@/features/chat/types";

/**
 * SessionsRepository interface for future storage/API implementations.
 * This interface defines the contract for managing conversations/sessions.
 */
export interface SessionsRepository {
  /**
   * List all sessions for a user
   */
  listSessions(userId: string): Promise<Conversation[]>;

  /**
   * Get a single session by ID
   */
  getSession(userId: string, sessionId: string): Promise<Conversation | null>;

  /**
   * Create a new session
   */
  createSession(userId: string): Promise<Conversation>;

  /**
   * Append a message to a session
   */
  appendMessage(
    userId: string,
    sessionId: string,
    message: Message
  ): Promise<void>;

  /**
   * Rename a session
   */
  renameSession(
    userId: string,
    sessionId: string,
    title: string
  ): Promise<void>;

  /**
   * Delete a session
   */
  deleteSession(userId: string, sessionId: string): Promise<void>;
}

/**
 * Storage keys for localStorage (for future use)
 */
export const STORAGE_KEYS = {
  USER_ID: "genshin:userId",
  SESSIONS: (userId: string) => `genshin:user:${userId}:sessions`,
  ACTIVE_SESSION: (userId: string) => `genshin:user:${userId}:activeSessionId`,
} as const;
