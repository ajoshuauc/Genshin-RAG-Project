"use client";

import { ConversationsSidebar } from "./ConversationsSidebar";
import { Header } from "./Header";
import { WelcomeEmptyState } from "./WelcomeEmptyState";
import { MessagesPanel } from "./MessagesPanel";
import { Composer } from "./Composer";
import { useConversations } from "../hooks/useConversations";
import { useChat } from "../hooks/useChat";
import { useSidebarDrawer } from "../hooks/useSidebarDrawer";

export function ChatPage() {
  const {
    conversations,
    activeConversation,
    activeConversationId,
    createConversation,
    selectConversation,
    updateConversation,
    updateConversationTitle,
  } = useConversations();

  const { messages, isTyping, sendMessage } = useChat({
    activeConversation,
    updateConversation,
    updateConversationTitle,
    createConversation,
  });

  const {
    isOpen: isSidebarOpen,
    isDesktop,
    toggle: toggleSidebar,
    close: closeSidebar,
    triggerRef,
    sidebarRef,
  } = useSidebarDrawer();

  const hasMessages = messages.length > 0;

  // Handle conversation selection on mobile (close sidebar after selection)
  const handleSelectConversation = (id: string) => {
    selectConversation(id);
    if (!isDesktop) {
      closeSidebar();
    }
  };

  // Handle new conversation on mobile (close sidebar after creation)
  const handleNewConversation = () => {
    createConversation();
    if (!isDesktop) {
      closeSidebar();
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden">
      {/* Sidebar - Desktop: static, Mobile: off-canvas drawer */}
      <ConversationsSidebar
        ref={sidebarRef}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onNewConversation={handleNewConversation}
        onSelectConversation={handleSelectConversation}
        isOpen={isSidebarOpen}
        isDesktop={isDesktop}
        onClose={closeSidebar}
      />

      {/* Overlay - Mobile only when sidebar is open */}
      {!isDesktop && (
        <div
          className={`fixed inset-0 z-40 transition-all duration-300 ${
            isSidebarOpen
              ? "opacity-100 pointer-events-auto"
              : "opacity-0 pointer-events-none"
          }`}
          onClick={closeSidebar}
          aria-hidden="true"
        >
          {/* Blur overlay with sidebar-matching tint */}
          <div className="absolute inset-0 bg-secondary/60 backdrop-blur-md" />
        </div>
      )}

      {/* Main content */}
      <main className="flex flex-col flex-1 h-full min-w-0 starfield">
        {/* Header with hamburger on mobile */}
        <Header
          triggerRef={triggerRef}
          isSidebarOpen={isSidebarOpen}
          isDesktop={isDesktop}
          onToggleSidebar={toggleSidebar}
        />

        {/* Messages or empty state */}
        {hasMessages ? (
          <MessagesPanel messages={messages} isTyping={isTyping} />
        ) : (
          <WelcomeEmptyState onSelectPrompt={sendMessage} />
        )}

        {/* Composer */}
        <Composer onSend={sendMessage} disabled={isTyping} />
      </main>
    </div>
  );
}
