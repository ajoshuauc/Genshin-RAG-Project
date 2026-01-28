"use client";

import { useState, FormEvent, KeyboardEvent } from "react";
import { Paperclip, Image as ImageIcon, Send } from "lucide-react";

interface ComposerProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function Composer({ onSend, disabled = false }: ComposerProps) {
  const [message, setMessage] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="py-4">
      {/* Centered content column */}
      <div className="w-full max-w-[900px] mx-auto px-4 lg:px-6">
        <form onSubmit={handleSubmit}>
          <div className="flex items-center gap-3 bg-glass rounded-2xl border border-border/50 px-4 py-3">
            {/* Left icons (visual only) */}
            <div className="flex items-center gap-2 text-foreground/40">
              <button
                type="button"
                className="p-1.5 hover:text-foreground/60 transition-colors"
                aria-label="Attach file"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <button
                type="button"
                className="p-1.5 hover:text-foreground/60 transition-colors"
                aria-label="Add image"
              >
                <ImageIcon className="w-5 h-5" />
              </button>
            </div>

            {/* Input */}
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Send a message to your companion..."
              disabled={disabled}
              rows={1}
              className="flex-1 bg-transparent text-foreground placeholder:text-foreground/40 outline-none resize-none max-h-32 leading-relaxed"
            />

            {/* Send button */}
            <button
              type="submit"
              disabled={!message.trim() || disabled}
              className="p-2 rounded-xl bg-primary/20 text-primary hover:bg-primary/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 hover:shadow-glow"
              aria-label="Send message"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>

        {/* Disclaimer */}
        <p className="text-center text-xs text-foreground/30 mt-3">
          This is a fictional AI companion. Responses are simulated for demonstration purposes.
        </p>
      </div>
    </div>
  );
}
