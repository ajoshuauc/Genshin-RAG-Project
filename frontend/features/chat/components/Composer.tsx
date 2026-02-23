"use client";

import { useState, useRef, useEffect, FormEvent, KeyboardEvent } from "react";
import { Send, X } from "lucide-react";

interface ComposerProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function Composer({ onSend, disabled = false }: ComposerProps) {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [message]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const isActive = message.trim() && !disabled;
  const hasText = message.trim().length > 0;

  const handleClear = () => {
    setMessage("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.focus();
    }
  };

  return (
    <div className="py-4 bg-gradient-to-t from-background via-background to-transparent">
      {/* Centered content column */}
      <div className="w-full max-w-[900px] mx-auto px-4 lg:px-6">
        <form onSubmit={handleSubmit}>
          <div className="relative flex items-end gap-3 bg-card rounded-2xl border border-border/50 genshin-border shadow-input pl-5 pr-4 py-3 overflow-hidden">
            {/* Shimmer overlay */}
            <div className="absolute inset-0 animate-shimmer pointer-events-none" />

            {/* Input */}
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Send a message to Genshin GPT..."
              disabled={disabled}
              rows={1}
              className="relative flex-1 bg-transparent text-foreground placeholder:text-foreground/40 outline-none resize-none max-h-[200px] leading-relaxed py-1"
            />

            {/* Action buttons */}
            <div className="relative flex items-center gap-2 mb-0.5 flex-shrink-0">
              {/* Clear button - only visible when there's text */}
              {hasText && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="p-2 rounded-xl text-foreground/40 hover:text-foreground/60 hover:bg-secondary/50 transition-all cursor-pointer"
                  aria-label="Clear message"
                >
                  <X className="w-5 h-5" />
                </button>
              )}

              {/* Send button */}
              <button
                type="submit"
                disabled={!message.trim() || disabled}
                className={`p-2 rounded-xl transition-all duration-200 ${
                  isActive
                    ? "bg-primary text-primary-foreground shadow-glow hover:shadow-glow-strong cursor-pointer"
                    : "bg-secondary text-muted-foreground cursor-not-allowed"
                }`}
                aria-label="Send message"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </form>

        {/* Disclaimer */}
        <p className="text-center text-xs text-foreground/30 mt-3">
          Disclaimer: Knowledge base is last updated on December 2025. Information may be incomplete.
        </p>
      </div>
    </div>
  );
}
