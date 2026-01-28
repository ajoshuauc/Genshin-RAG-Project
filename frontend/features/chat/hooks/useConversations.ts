"use client";

import { useState, useCallback } from "react";
import { Conversation } from "../types";
import {
  getPlaceholderConversations,
  createNewConversation,
  deriveTitleFromMessage,
} from "../lib/placeholders";

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    getPlaceholderConversations()
  );
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId
  ) ?? null;

  const createConversation = useCallback(() => {
    const newConversation = createNewConversation();
    setConversations((prev) => [newConversation, ...prev]);
    setActiveConversationId(newConversation.id);
    return newConversation;
  }, []);

  const selectConversation = useCallback((conversationId: string) => {
    setActiveConversationId(conversationId);
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
    createConversation,
    selectConversation,
    updateConversation,
    updateConversationTitle,
    deleteConversation,
  };
}
