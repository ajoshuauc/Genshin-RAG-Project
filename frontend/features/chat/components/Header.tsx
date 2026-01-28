"use client";

import { RefObject } from "react";
import { Sparkles, Menu } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

interface HeaderProps {
  triggerRef: RefObject<HTMLButtonElement | null>;
  isSidebarOpen: boolean;
  isDesktop: boolean;
  onToggleSidebar: () => void;
}

export function Header({
  triggerRef,
  isSidebarOpen,
  isDesktop,
  onToggleSidebar,
}: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-4 lg:px-6 py-4 border-b border-border/30">
      <div className="flex items-center gap-3">
        {/* Hamburger menu - mobile only */}
        {!isDesktop && (
          <button
            ref={triggerRef}
            onClick={onToggleSidebar}
            className="p-2 -ml-2 text-foreground/60 hover:text-foreground hover:bg-secondary/50 rounded-lg transition-colors"
            aria-controls="sidebar"
            aria-expanded={isSidebarOpen}
            aria-label={isSidebarOpen ? "Close menu" : "Open menu"}
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Logo and title */}
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/20 text-primary">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-gradient-gold font-[family-name:var(--font-cinzel)]">
            Genshin Chat Companion
          </h1>
          <p className="text-sm text-foreground/50 hidden sm:block">
            Your guide through Teyvat
          </p>
        </div>
      </div>
      <Badge variant="success">
        <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        Online
      </Badge>
    </header>
  );
}
