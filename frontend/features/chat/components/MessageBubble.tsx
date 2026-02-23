"use client";

import { useState } from "react";
import { User, Sparkles, Copy, Check } from "lucide-react";
import { Message } from "../types";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`group flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} animate-fade-in`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? "bg-bubble-user text-foreground"
            : "bg-gradient-to-br from-primary/20 to-accent/20 genshin-border text-primary"
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : (
          <Sparkles className="w-4 h-4" />
        )}
      </div>

      {/* Bubble and actions */}
      <div className={`flex flex-col max-w-[70%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`relative px-4 py-3 rounded-2xl ${
            isUser
              ? "bg-bubble-user text-foreground rounded-tr-sm"
              : "bg-bubble-ai text-foreground rounded-tl-sm genshin-border"
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>

        {/* Copy button - always visible on mobile (no box); box on desktop hover */}
        <button
          onClick={handleCopy}
          className={`mt-1.5 p-1.5 rounded-md text-foreground/40 hover:text-foreground/60 transition-all cursor-pointer ${
            isUser
              ? "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:border sm:border-border/30 sm:bg-secondary/30 hover:bg-secondary/60 sm:hover:bg-secondary/60"
              : "border-transparent bg-transparent sm:hover:border-border/30 sm:hover:bg-secondary/30"
          }`}
          aria-label={copied ? "Copied" : "Copy message"}
        >
          {copied ? (
            <Check className="w-4 h-4 text-green-500" />
          ) : (
            <Copy className="w-4 h-4" />
          )}
        </button>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-in">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-br from-primary/20 to-accent/20 genshin-border text-primary">
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

function SkeletonBubble({ isUser, width }: { isUser: boolean; width: string }) {
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar skeleton */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full animate-pulse ${
          isUser ? "bg-foreground/10" : "bg-primary/10"
        }`}
      />
      {/* Bubble skeleton */}
      <div
        className={`h-12 rounded-2xl animate-pulse ${width} ${
          isUser
            ? "bg-foreground/10 rounded-tr-sm"
            : "bg-foreground/5 rounded-tl-sm"
        }`}
      />
    </div>
  );
}

export function TranscriptSkeleton() {
  return (
    <div className="flex-1 flex flex-col gap-4 p-4 lg:p-6 overflow-hidden animate-fade-in">
      <div className="w-full max-w-[900px] mx-auto space-y-4">
        {/* Simulate a conversation pattern */}
        <SkeletonBubble isUser={true} width="w-[45%] sm:w-[35%]" />
        <SkeletonBubble isUser={false} width="w-[70%] sm:w-[55%]" />
        <SkeletonBubble isUser={true} width="w-[50%] sm:w-[40%]" />
        <SkeletonBubble isUser={false} width="w-[60%] sm:w-[50%]" />
      </div>
    </div>
  );
}
