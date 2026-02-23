"use client";

import { Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { QuickPrompts } from "./QuickPrompts";

interface WelcomeEmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

export function WelcomeEmptyState({ onSelectPrompt }: WelcomeEmptyStateProps) {
  return (
    <div className="flex-1 flex items-center justify-center py-8 overflow-y-auto">
      {/* Centered content column */}
      <div className="w-full max-w-[900px] mx-auto px-4 lg:px-6">
        <motion.div
          className="flex flex-col items-center"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        >
          {/* Icon */}
          <div className="flex items-center justify-center w-20 h-20 mb-6 rounded-full bg-gradient-to-br from-primary/15 to-accent/20 genshin-border animate-float">
            <Sparkles className="w-10 h-10 text-primary" />
          </div>

          {/* Title */}
          <h2 className="text-2xl md:text-3xl font-semibold text-gradient-gold mb-4 font-[family-name:var(--font-cinzel)] tracking-wide text-center">
            Welcome, Traveler
          </h2>

          {/* Description */}
          <p className="text-center text-muted-foreground max-w-md mb-8 text-sm md:text-base leading-relaxed">
            Greetings! I&apos;m your companion on this journey through Teyvat. Ask me
            anything about the world, its lore, or seek guidance on your adventures.
          </p>

          {/* Quick prompts */}
          <QuickPrompts onSelectPrompt={onSelectPrompt} />
        </motion.div>
      </div>
    </div>
  );
}
