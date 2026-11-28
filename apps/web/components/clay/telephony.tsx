"use client";

import type { ReactNode } from "react";
import { Delete, Phone, PhoneOff } from "lucide-react";

const DIAL_KEYS = [
  { digit: "1", letters: "" },
  { digit: "2", letters: "ABC" },
  { digit: "3", letters: "DEF" },
  { digit: "4", letters: "GHI" },
  { digit: "5", letters: "JKL" },
  { digit: "6", letters: "MNO" },
  { digit: "7", letters: "PQRS" },
  { digit: "8", letters: "TUV" },
  { digit: "9", letters: "WXYZ" },
  { digit: "*", letters: "" },
  { digit: "0", letters: "+" },
  { digit: "#", letters: "" },
];

export function ClayDialPad({
  value,
  onChange,
  onDigitPress,
  onCall,
  onHangup,
  inCall = false,
  canCall = true,
  placeholder = "Enter extension or number",
}: {
  value: string;
  onChange: (next: string) => void;
  onDigitPress?: (digit: string) => void;
  onCall: () => void;
  onHangup: () => void;
  inCall?: boolean;
  canCall?: boolean;
  placeholder?: string;
}) {
  const handlePress = (digit: string) => {
    onChange(value + digit);
    onDigitPress?.(digit);
  };

  return (
    <div className="clay-card space-y-4 p-5">
      {/* Number Display */}
      <div className="clay-inset flex items-center gap-2 rounded-2xl px-4 py-3">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          aria-label="Phone number or extension"
          className="w-full bg-transparent text-center font-mono text-xl font-semibold tracking-wider text-foreground shadow-none focus:outline-none"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange(value.slice(0, -1))}
            aria-label="Backspace"
            className="clay-btn rounded-xl p-2 text-muted-foreground hover:text-foreground"
          >
            <Delete className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* 0-9 Keypad */}
      <div className="grid grid-cols-3 gap-3">
        {DIAL_KEYS.map((k) => (
          <button
            key={k.digit}
            type="button"
            onClick={() => handlePress(k.digit)}
            className="clay-btn flex flex-col items-center justify-center rounded-2xl bg-card py-3 text-foreground"
          >
            <span className="text-lg font-semibold leading-none">{k.digit}</span>
            <span className="mt-1 text-[10px] tracking-widest text-muted-foreground">
              {k.letters || "\u00A0"}
            </span>
          </button>
        ))}
      </div>

      {/* Primary Call / Hangup Action */}
      <div className="pt-1">
        {inCall ? (
          <button
            type="button"
            onClick={onHangup}
            className="clay-btn flex w-full items-center justify-center gap-2 rounded-2xl bg-[#DF6F79] py-3.5 text-sm font-semibold text-white"
          >
            <PhoneOff className="h-4 w-4" />
            End Call
          </button>
        ) : (
          <button
            type="button"
            disabled={!canCall || !value.trim()}
            onClick={onCall}
            className="clay-btn flex w-full items-center justify-center gap-2 rounded-2xl bg-[#42A889] py-3.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            <Phone className="h-4 w-4" />
            Place Call
          </button>
        )}
      </div>
    </div>
  );
}

export function ClayCallControl({
  icon,
  label,
  active = false,
  danger = false,
  disabled = false,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  active?: boolean;
  danger?: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      aria-pressed={active}
      className={`clay-btn flex flex-col items-center justify-center gap-1.5 rounded-2xl px-3 py-3 text-xs font-medium disabled:opacity-50 ${
        danger
          ? "bg-[#DF6F79] text-white"
          : active
            ? "bg-primary text-primary-foreground"
            : "bg-card text-foreground"
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

export function ClayAudioVisualizer({
  active = false,
  bars = 12,
  level = 0.5,
  label = "Audio level",
}: {
  active?: boolean;
  bars?: number;
  level?: number;
  label?: string;
}) {
  const clamped = Math.max(0.1, Math.min(1, level));
  return (
    <div
      className="clay-inset flex h-12 items-center justify-center gap-1.5 rounded-2xl px-4"
      aria-label={label}
    >
      {Array.from({ length: bars }).map((_, idx) => {
        const wave = Math.sin((idx + 1) * 0.85) * 0.35 + 0.65;
        const heightPct = active ? Math.max(20, Math.round(wave * clamped * 100)) : 18;
        return (
          <span
            key={idx}
            className={`w-1.5 rounded-full transition-all duration-150 ${
              active ? "bg-primary" : "bg-muted-foreground/30"
            }`}
            style={{ height: `${heightPct}%` }}
          />
        );
      })}
    </div>
  );
}
