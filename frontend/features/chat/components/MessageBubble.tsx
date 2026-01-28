"use client";

import { User, Sparkles } from "lucide-react";
import { Message } from "../types";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} animate-fade-in`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
          isUser
            ? "bg-bubble-user text-foreground"
            : "bg-primary/20 text-primary"
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : (
          <Sparkles className="w-4 h-4" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={`relative max-w-[70%] px-4 py-3 rounded-2xl ${
          isUser
            ? "bg-bubble-user text-foreground rounded-tr-sm"
            : "bg-bubble-ai text-foreground rounded-tl-sm genshin-border"
        }`}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </p>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-in">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-primary/20 text-primary">
        <Sparkles className="w-4 h-4" />
      </div>

      {/* Typing dots */}
      <div className="bg-bubble-ai rounded-2xl rounded-tl-sm px-4 py-3 genshin-border">
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-foreground/40 animate-typing-dot" />
          <span className="w-2 h-2 rounded-full bg-foreground/40 animate-typing-dot-delay-1" />
          <span className="w-2 h-2 rounded-full bg-foreground/40 animate-typing-dot-delay-2" />
        </div>
      </div>
    </div>
  );
}
