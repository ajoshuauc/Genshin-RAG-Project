"use client";

import { useState, useCallback } from "react";
import { Message, Conversation } from "../types";
import {
  createMessage,
  generatePlaceholderResponse,
} from "../lib/placeholders";

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

      // If no active conversation, create one
      let conversation = activeConversation;
      if (!conversation) {
        conversation = createConversation();
      }

      const userMessage = createMessage("user", content.trim());
      const isFirstMessage = conversation.messages.length === 0;

      // Add user message immediately
      const updatedMessages = [...conversation.messages, userMessage];
      updateConversation(conversation.id, { messages: updatedMessages });

      // Update title if this is the first message
      if (isFirstMessage) {
        updateConversationTitle(conversation.id, content.trim());
      }

      // Show typing indicator
      setIsTyping(true);

      // Simulate assistant response delay (200-600ms)
      const delay = 200 + Math.random() * 400;
      await new Promise((resolve) => setTimeout(resolve, delay));

      // Generate placeholder response
      const responseContent = generatePlaceholderResponse(content);
      const assistantMessage = createMessage("assistant", responseContent);

      // Add assistant message
      updateConversation(conversation.id, {
        messages: [...updatedMessages, assistantMessage],
      });

      setIsTyping(false);
    },
    [activeConversation, updateConversation, updateConversationTitle, createConversation]
  );

  return {
    messages: activeConversation?.messages ?? [],
    isTyping,
    sendMessage,
  };
}
