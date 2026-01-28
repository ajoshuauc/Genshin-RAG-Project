"use client";

import { HTMLAttributes, forwardRef } from "react";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "accent";
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className = "", variant = "default", children, ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full";

    const variantStyles = {
      default: "bg-secondary text-foreground border border-border/50",
      success: "bg-green-500/20 text-green-400 border border-green-500/30",
      warning: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
      accent: "bg-accent/20 text-accent border border-accent/30",
    };

    return (
      <span
        ref={ref}
        className={`${baseStyles} ${variantStyles[variant]} ${className}`}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = "Badge";
