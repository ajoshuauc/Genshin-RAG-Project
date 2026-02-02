"use client";

import { useState, useCallback } from "react";
import { Message, Conversation } from "../types";
import { createMessage } from "../lib/placeholders";
import { getOrCreateUserId } from "@/lib/sessions/user";
import { apiRepo } from "@/lib/sessions/apiRepo";

interface UseChatOptions {
  activeConversation: Conversation | null;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  updateConversationTitle: (id: string, firstMessage: string) => void;
  createConversation: () => Conversation;
}

export function useChat({
  activeConversation,
  updateConversation,
  updateConversationTitle,
  createConversation,
}: UseChatOptions) {
  const [isTyping, setIsTyping] = useState(false);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      const userId = getOrCreateUserId();
      if (!userId) {
        console.error("No user ID available");
        return;
      }

      // If no active conversation, create one
      let conversation = activeConversation;
      if (!conversation) {
        conversation = createConversation();
      }

      const userMessage = createMessage("user", content.trim());
      const isFirstMessage = conversation.messages.length === 0;

      // Add user message immediately (optimistic update)
      const updatedMessages = [...conversation.messages, userMessage];
      updateConversation(conversation.id, { messages: updatedMessages });

      // Update title if this is the first message
      if (isFirstMessage) {
        updateConversationTitle(conversation.id, content.trim());
      }

      // Show typing indicator
      setIsTyping(true);

      try {
        // Call the backend API
        const response = await apiRepo.sendChatMessage(
          userId,
          conversation.id, // This is the session_id
          content.trim()
        );

        // Create assistant message from response
        const assistantMessage = createMessage("assistant", response.response);

        // Add assistant message
        updateConversation(conversation.id, {
          messages: [...updatedMessages, assistantMessage],
        });
      } catch (error) {
        console.error("Failed to send message:", error);
        // Add error message
        const errorMessage = createMessage(
          "assistant",
          "Sorry, I encountered an error. Please try again."
        );
        updateConversation(conversation.id, {
          messages: [...updatedMessages, errorMessage],
        });
      } finally {
        setIsTyping(false);
      }
    },
    [activeConversation, updateConversation, updateConversationTitle, createConversation]
  );

  return {
    messages: activeConversation?.messages ?? [],
    isTyping,
    sendMessage,
  };
}
