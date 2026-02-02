"use client";

import { useState, useCallback, useEffect } from "react";
import { Conversation } from "../types";
import {
  createNewConversation,
  deriveTitleFromMessage,
} from "../lib/placeholders";
import { getOrCreateUserId } from "@/lib/sessions/user";
import { apiRepo } from "@/lib/sessions/apiRepo";

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load sessions from backend on mount
  useEffect(() => {
    const loadSessions = async () => {
      const userId = getOrCreateUserId();
      if (!userId) {
        setIsLoading(false);
        return;
      }

      try {
        const sessions = await apiRepo.listSessions(userId);
        setConversations(sessions);
      } catch (error) {
        console.error("Failed to load sessions:", error);
        // Start with empty list on error
        setConversations([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadSessions();
  }, []);

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId
  ) ?? null;

  // Load transcript when selecting a conversation
  const selectConversation = useCallback(async (conversationId: string) => {
    setActiveConversationId(conversationId);

    const userId = getOrCreateUserId();
    if (!userId) return;

    // Check if we already have messages loaded
    const existing = conversations.find((c) => c.id === conversationId);
    if (existing && existing.messages.length > 0) {
      return; // Already loaded
    }

    try {
      const session = await apiRepo.getSession(userId, conversationId);
      if (session) {
        setConversations((prev) =>
          prev.map((c) =>
            c.id === conversationId
              ? { ...c, messages: session.messages, title: session.title }
              : c
          )
        );
      }
    } catch (error) {
      console.error("Failed to load session transcript:", error);
    }
  }, [conversations]);

  const createConversation = useCallback(() => {
    const newConversation = createNewConversation();
    setConversations((prev) => [newConversation, ...prev]);
    setActiveConversationId(newConversation.id);
    return newConversation;
  }, []);

  const updateConversation = useCallback(
    (conversationId: string, updates: Partial<Conversation>) => {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === conversationId
            ? { ...c, ...updates, updatedAt: new Date() }
            : c
        )
      );
    },
    []
  );

  const updateConversationTitle = useCallback(
    (conversationId: string, firstMessage: string) => {
      const title = deriveTitleFromMessage(firstMessage);
      updateConversation(conversationId, { title });
    },
    [updateConversation]
  );

  const deleteConversation = useCallback((conversationId: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== conversationId));
    setActiveConversationId((currentId) =>
      currentId === conversationId ? null : currentId
    );
  }, []);

  // Sort conversations by updatedAt (most recent first)
  const sortedConversations = [...conversations].sort(
    (a, b) => b.updatedAt.getTime() - a.updatedAt.getTime()
  );

  return {
    conversations: sortedConversations,
    activeConversation,
    activeConversationId,
    isLoading,
    createConversation,
    selectConversation,
    updateConversation,
    updateConversationTitle,
    deleteConversation,
  };
}
