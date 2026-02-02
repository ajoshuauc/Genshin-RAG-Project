import { Conversation, Message } from "../types";

// Quick prompt suggestions
export const QUICK_PROMPTS = [
  "Tell me about Mondstadt",
  "Best team compositions",
  "Explain elemental reactions",
];

// Generate a unique UUID
export function generateId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Return empty array - sessions come from backend now
export function getPlaceholderConversations(): Conversation[] {
  return [];
}

// Create a new empty conversation (id is session_id)
export function createNewConversation(): Conversation {
  const now = new Date();
  return {
    id: generateId(), // This is the session_id (UUID)
    title: "New Conversation",
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

// Create a message
export function createMessage(role: "user" | "assistant", content: string): Message {
  return {
    id: generateId(),
    role,
    content,
    createdAt: new Date(),
  };
}

// Derive title from first user message
export function deriveTitleFromMessage(message: string): string {
  const maxLength = 25;
  const cleaned = message.trim();
  if (cleaned.length <= maxLength) {
    return cleaned;
  }
  return cleaned.substring(0, maxLength) + "...";
}
