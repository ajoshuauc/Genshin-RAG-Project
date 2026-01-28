"use client";

import { forwardRef } from "react";
import { Plus, MessageSquare, Settings, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Conversation } from "../types";
import { formatRelativeTime } from "../lib/time";

interface ConversationsSidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  isOpen: boolean;
  isDesktop: boolean;
  onClose: () => void;
}

export const ConversationsSidebar = forwardRef<
  HTMLElement,
  ConversationsSidebarProps
>(function ConversationsSidebar(
  {
    conversations,
    activeConversationId,
    onNewConversation,
    onSelectConversation,
    isOpen,
    isDesktop,
    onClose,
  },
  ref
) {
  // Desktop: static sidebar, always visible
  // Mobile: off-canvas drawer with slide animation
  const sidebarClasses = isDesktop
    ? "relative flex flex-col w-[280px] h-full bg-secondary/30 border-r border-border/30"
    : `fixed inset-y-0 left-0 z-50 flex flex-col w-[280px] h-full bg-secondary/95 border-r border-border/30 transform transition-transform duration-300 ease-in-out ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`;

  return (
    <aside
      ref={ref}
      className={sidebarClasses}
      role={isDesktop ? undefined : "dialog"}
      aria-modal={isDesktop ? undefined : true}
      aria-label="Conversations sidebar"
      id="sidebar"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-primary font-[family-name:var(--font-cinzel)]">
          Conversations
        </h2>
        {/* Close button - mobile only */}
        {!isDesktop && (
          <button
            onClick={onClose}
            className="p-1.5 text-foreground/60 hover:text-foreground hover:bg-secondary/50 rounded-lg transition-colors"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* New Conversation button */}
      <div className="px-4 pb-4">
        <Button
          variant="secondary"
          className="w-full justify-start gap-2 genshin-border"
          onClick={onNewConversation}
        >
          <Plus className="w-4 h-4" />
          New Conversation
        </Button>
      </div>

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto px-2">
        <p className="px-2 py-2 text-xs text-foreground/40 uppercase tracking-wide">
          Recent chats
        </p>
        <ul className="space-y-1">
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <button
                onClick={() => onSelectConversation(conversation.id)}
                className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                  activeConversationId === conversation.id
                    ? "bg-secondary/80 border border-primary/30"
                    : "hover:bg-secondary/50 border border-transparent"
                }`}
              >
                <MessageSquare className="w-4 h-4 mt-0.5 text-foreground/50 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground truncate">
                    {conversation.title}
                  </p>
                  <p className="text-xs text-foreground/40">
                    {formatRelativeTime(conversation.updatedAt)}
                  </p>
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border/30">
        <button className="flex items-center gap-3 w-full px-3 py-2 text-sm text-foreground/60 hover:text-foreground hover:bg-secondary/50 rounded-lg transition-colors">
          <Settings className="w-4 h-4" />
          Settings
        </button>
      </div>
    </aside>
  );
});
