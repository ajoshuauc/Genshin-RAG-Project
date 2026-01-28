"use client";

import { QUICK_PROMPTS } from "../lib/placeholders";

interface QuickPromptsProps {
  onSelectPrompt: (prompt: string) => void;
}

export function QuickPrompts({ onSelectPrompt }: QuickPromptsProps) {
  return (
    <div className="flex flex-wrap justify-center gap-2 sm:gap-3">
      {QUICK_PROMPTS.map((prompt) => (
        <button
          key={prompt}
          onClick={() => onSelectPrompt(prompt)}
          className="px-3 sm:px-4 py-2 text-xs sm:text-sm bg-secondary/60 border border-border/50 rounded-full text-foreground/80 hover:bg-secondary hover:border-primary/30 hover:text-foreground transition-all duration-200"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}
