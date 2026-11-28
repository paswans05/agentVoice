"use client";

import {
  forwardRef,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { Loader2 } from "lucide-react";

export type ClayButtonVariant = "primary" | "secondary" | "success" | "warning" | "danger" | "ghost";

const BUTTON_VARIANTS: Record<ClayButtonVariant, string> = {
  primary:
    "bg-primary text-primary-foreground border border-white/20",
  secondary:
    "bg-card text-foreground border border-border/70",
  success:
    "bg-[#42A889] text-white border border-white/20",
  warning:
    "bg-[#E5A64B] text-[#252B35] border border-white/25",
  danger:
    "bg-[#DF6F79] text-white border border-white/20",
  ghost:
    "bg-transparent text-muted-foreground hover:bg-muted/70 hover:text-foreground shadow-none",
};

export interface ClayButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ClayButtonVariant;
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

export const ClayButton = forwardRef<HTMLButtonElement, ClayButtonProps>(
  ({ variant = "secondary", size = "md", loading = false, className = "", children, disabled, ...props }, ref) => {
    const sizeCls =
      size === "sm"
        ? "px-3 py-1.5 text-xs"
        : size === "lg"
          ? "px-5 py-3 text-sm"
          : "px-4 py-2 text-xs sm:text-sm";
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`clay-btn inline-flex items-center justify-center gap-2 font-medium disabled:pointer-events-none disabled:opacity-50 ${BUTTON_VARIANTS[variant]} ${sizeCls} ${className}`}
        {...props}
      >
        {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
        {children}
      </button>
    );
  },
);
ClayButton.displayName = "ClayButton";

export interface ClayIconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ClayButtonVariant;
  label: string;
}

export const ClayIconButton = forwardRef<HTMLButtonElement, ClayIconButtonProps>(
  ({ variant = "secondary", label, className = "", children, ...props }, ref) => (
    <button
      ref={ref}
      aria-label={label}
      title={label}
      className={`clay-btn inline-flex h-9 w-9 items-center justify-center rounded-xl disabled:pointer-events-none disabled:opacity-50 ${BUTTON_VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  ),
);
ClayIconButton.displayName = "ClayIconButton";

export const ClayInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className = "", ...props }, ref) => (
    <input
      ref={ref}
      className={`clay-inset w-full px-3.5 py-2 text-sm text-foreground placeholder:text-muted-foreground/75 focus:outline-none disabled:opacity-50 ${className}`}
      {...props}
    />
  ),
);
ClayInput.displayName = "ClayInput";

export const ClaySelect = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className = "", children, ...props }, ref) => (
    <select
      ref={ref}
      className={`clay-inset w-full px-3.5 py-2 text-sm text-foreground focus:outline-none disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </select>
  ),
);
ClaySelect.displayName = "ClaySelect";

export const ClayTextarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className = "", ...props }, ref) => (
    <textarea
      ref={ref}
      className={`clay-inset w-full px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/75 focus:outline-none disabled:opacity-50 ${className}`}
      {...props}
    />
  ),
);
ClayTextarea.displayName = "ClayTextarea";

export function ClayCheckbox({
  checked,
  onChange,
  label,
  disabled = false,
  className = "",
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <label className={`inline-flex cursor-pointer items-center gap-2.5 text-sm ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className}`}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded-md accent-[#7467D8]"
      />
      {label && <span className="text-foreground">{label}</span>}
    </label>
  );
}

export function ClaySwitch({
  checked,
  onChange,
  label,
  disabled = false,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="inline-flex items-center gap-2.5 text-sm disabled:opacity-50"
    >
      <span
        className={`clay-inset relative inline-flex h-6 w-11 shrink-0 items-center rounded-full p-0.5 transition-colors ${
          checked ? "bg-primary/85" : "bg-muted"
        }`}
      >
        <span
          className={`h-4 w-4 rounded-full bg-card shadow-clay-sm transition-transform ${
            checked ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </span>
      {label && <span className="text-foreground">{label}</span>}
    </button>
  );
}
