import { Conversation, Message } from "@/features/chat/types";
import { SessionsRepository } from "./repo";

/**
 * LocalStorage-based implementation of SessionsRepository.
 * STUB: Not implemented yet. This will be wired up for localStorage persistence.
 */
export class LocalStorageSessionsRepository implements SessionsRepository {
  async listSessions(_userId: string): Promise<Conversation[]> {
    throw new Error("LocalStorageSessionsRepository.listSessions: Not implemented");
  }

  async getSession(
    _userId: string,
    _sessionId: string
  ): Promise<Conversation | null> {
    throw new Error("LocalStorageSessionsRepository.getSession: Not implemented");
  }

  async createSession(_userId: string): Promise<Conversation> {
    throw new Error("LocalStorageSessionsRepository.createSession: Not implemented");
  }

  async appendMessage(
    _userId: string,
    _sessionId: string,
    _message: Message
  ): Promise<void> {
    throw new Error("LocalStorageSessionsRepository.appendMessage: Not implemented");
  }

  async renameSession(
    _userId: string,
    _sessionId: string,
    _title: string
  ): Promise<void> {
    throw new Error("LocalStorageSessionsRepository.renameSession: Not implemented");
  }

  async deleteSession(_userId: string, _sessionId: string): Promise<void> {
    throw new Error("LocalStorageSessionsRepository.deleteSession: Not implemented");
  }
}

/**
 * Singleton instance (for future use)
 */
export const localRepo = new LocalStorageSessionsRepository();
