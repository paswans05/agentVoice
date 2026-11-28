"use client";

import type { ReactNode } from "react";

export type ClayAccent = "default" | "lavender" | "mint" | "peach" | "sky" | "coral";

const ACCENT_SURFACE: Record<ClayAccent, string> = {
  default: "",
  lavender: "bg-gradient-to-br from-[#7467D8]/12 via-card to-card",
  mint: "bg-gradient-to-br from-[#42A889]/12 via-card to-card",
  peach: "bg-gradient-to-br from-[#E5A64B]/14 via-card to-card",
  sky: "bg-gradient-to-br from-[#6499D5]/12 via-card to-card",
  coral: "bg-gradient-to-br from-[#DF6F79]/12 via-card to-card",
};

export function ClayCard({
  children,
  className = "",
  hover = false,
  accent = "default",
  padding = "p-5",
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  accent?: ClayAccent;
  padding?: string;
}) {
  return (
    <div
      className={`clay-card ${hover ? "clay-card-hover" : ""} ${ACCENT_SURFACE[accent]} ${padding} ${className}`}
    >
      {children}
    </div>
  );
}

export type ClayBadgeTone = "primary" | "success" | "warning" | "danger" | "info" | "neutral";

const BADGE_TONES: Record<ClayBadgeTone, string> = {
  primary: "bg-[#7467D8]/15 text-[#5D50C4] dark:text-[#A99FF5] border-[#7467D8]/30",
  success: "bg-[#42A889]/15 text-[#2C8469] dark:text-[#66CCA9] border-[#42A889]/30",
  warning: "bg-[#E5A64B]/18 text-[#A66E1B] dark:text-[#F2BE6B] border-[#E5A64B]/30",
  danger: "bg-[#DF6F79]/16 text-[#B64450] dark:text-[#F08C95] border-[#DF6F79]/30",
  info: "bg-[#6499D5]/15 text-[#3B71AD] dark:text-[#8CB9EB] border-[#6499D5]/30",
  neutral: "bg-muted/85 text-muted-foreground border-border/70",
};

export function ClayBadge({
  children,
  tone = "neutral",
  dot = false,
  className = "",
}: {
  children: ReactNode;
  tone?: ClayBadgeTone;
  dot?: boolean;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium shadow-clay-sm ${BADGE_TONES[tone]} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

export function ClayStatCard({
  label,
  value,
  sublabel,
  icon,
  accent = "default",
  badge,
  className = "",
}: {
  label: string;
  value: ReactNode;
  sublabel?: ReactNode;
  icon?: ReactNode;
  accent?: ClayAccent;
  badge?: ReactNode;
  className?: string;
}) {
  return (
    <ClayCard hover accent={accent} className={className}>
      <div className="flex items-center justify-between gap-2 text-xs font-medium text-muted-foreground">
        <span>{label}</span>
        {icon && (
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-muted/70 text-primary shadow-clay-inset">
            {icon}
          </span>
        )}
      </div>
      <div className="mt-3 flex items-center gap-2 text-2xl font-semibold tracking-tight text-foreground">
        {value}
        {badge}
      </div>
      {sublabel && <p className="mt-1.5 text-xs text-muted-foreground">{sublabel}</p>}
    </ClayCard>
  );
}

export function ClayProgress({
  value,
  max = 100,
  tone = "primary",
  label,
  className = "",
}: {
  value: number;
  max?: number;
  tone?: "primary" | "success" | "warning" | "danger" | "info";
  label?: string;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / Math.max(1, max)) * 100));
  const barTone = {
    primary: "bg-primary",
    success: "bg-[#42A889]",
    warning: "bg-[#E5A64B]",
    danger: "bg-[#DF6F79]",
    info: "bg-[#6499D5]",
  }[tone];

  return (
    <div className={`space-y-1.5 ${className}`}>
      {label && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{label}</span>
          <span className="font-medium text-foreground">{Math.round(pct)}%</span>
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        className="clay-inset h-3 w-full overflow-hidden rounded-full p-0.5"
      >
        <div
          className={`h-full rounded-full transition-all duration-300 ${barTone}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function ClayChartContainer({
  title,
  subtitle,
  actions,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <ClayCard className={`space-y-4 ${className}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        {actions}
      </div>
      <div className="clay-inset rounded-2xl p-4">{children}</div>
    </ClayCard>
  );
}
