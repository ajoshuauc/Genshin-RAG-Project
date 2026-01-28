"use client";

import { InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={`w-full bg-transparent text-foreground placeholder:text-foreground/40 outline-none ${className}`}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";
