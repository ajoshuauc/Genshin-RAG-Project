"use client";

import { useState, useCallback, useEffect, useRef } from "react";

interface UseSidebarDrawerOptions {
  /** Breakpoint width in pixels for desktop mode (sidebar always visible) */
  desktopBreakpoint?: number;
}

export function useSidebarDrawer(options: UseSidebarDrawerOptions = {}) {
  const { desktopBreakpoint = 1024 } = options; // lg breakpoint
  const [isOpen, setIsOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);

  // Check if we're on desktop
  useEffect(() => {
    const checkDesktop = () => {
      setIsDesktop(window.innerWidth >= desktopBreakpoint);
    };

    checkDesktop();
    window.addEventListener("resize", checkDesktop);
    return () => window.removeEventListener("resize", checkDesktop);
  }, [desktopBreakpoint]);

  // Close sidebar when switching to desktop
  useEffect(() => {
    if (isDesktop && isOpen) {
      setIsOpen(false);
    }
  }, [isDesktop, isOpen]);

  // Handle body scroll lock
  useEffect(() => {
    if (isOpen && !isDesktop) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen, isDesktop]);

  // Handle Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isDesktop) {
        close();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, isDesktop]);

  // Focus management
  useEffect(() => {
    if (isOpen && !isDesktop && sidebarRef.current) {
      // Focus first focusable element in sidebar
      const focusable = sidebarRef.current.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      focusable?.focus();
    }
  }, [isOpen, isDesktop]);

  const open = useCallback(() => {
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    // Return focus to trigger
    triggerRef.current?.focus();
  }, []);

  const toggle = useCallback(() => {
    if (isOpen) {
      close();
    } else {
      open();
    }
  }, [isOpen, open, close]);

  return {
    isOpen,
    isDesktop,
    open,
    close,
    toggle,
    triggerRef,
    sidebarRef,
  };
}
