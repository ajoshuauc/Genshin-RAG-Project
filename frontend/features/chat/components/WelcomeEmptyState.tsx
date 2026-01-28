"use client";

import { Sparkles } from "lucide-react";
import { QuickPrompts } from "./QuickPrompts";

interface WelcomeEmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

export function WelcomeEmptyState({ onSelectPrompt }: WelcomeEmptyStateProps) {
  return (
    <div className="flex-1 flex items-center justify-center py-8 overflow-y-auto">
      {/* Centered content column */}
      <div className="w-full max-w-[900px] mx-auto px-4 lg:px-6">
        <div className="flex flex-col items-center animate-fade-in">
          {/* Icon */}
          <div className="flex items-center justify-center w-20 h-20 mb-6 rounded-2xl bg-primary/20 shadow-glow animate-float">
            <Sparkles className="w-10 h-10 text-primary" />
          </div>

          {/* Title */}
          <h2 className="text-2xl sm:text-3xl font-semibold text-gradient-gold mb-4 font-[family-name:var(--font-cinzel)] tracking-wide text-center">
            Welcome, Traveler
          </h2>

          {/* Description */}
          <p className="text-center text-foreground/60 max-w-md mb-8 leading-relaxed">
            Greetings! I&apos;m your companion on this journey through Teyvat. Ask me
            anything about the world, its lore, or seek guidance on your adventures.
          </p>

          {/* Quick prompts */}
          <QuickPrompts onSelectPrompt={onSelectPrompt} />
        </div>
      </div>
    </div>
  );
}
