"use client";

import { useEffect, useRef } from "react";
import { Message } from "../types";
import { MessageBubble, TypingIndicator } from "./MessageBubble";

interface MessagesPanelProps {
  messages: Message[];
  isTyping: boolean;
}

export function MessagesPanel({ messages, isTyping }: MessagesPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto py-4"
    >
      {/* Centered content column */}
      <div className="w-full max-w-[900px] mx-auto px-4 lg:px-6 space-y-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isTyping && <TypingIndicator />}
      </div>
    </div>
  );
}
