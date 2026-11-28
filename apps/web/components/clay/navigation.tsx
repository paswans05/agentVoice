"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown, X } from "lucide-react";

export interface ClayTabItem {
  id: string;
  label: string;
  badge?: ReactNode;
}

export function ClayTabs({
  tabs,
  activeTab,
  onChange,
  className = "",
}: {
  tabs: ClayTabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={`clay-inset inline-flex flex-wrap gap-1.5 rounded-2xl p-1.5 ${className}`}
    >
      {tabs.map((t) => {
        const active = t.id === activeTab;
        return (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(t.id)}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-medium transition-all ${
              active
                ? "bg-card text-primary shadow-clay-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <span>{t.label}</span>
            {t.badge}
          </button>
        );
      })}
    </div>
  );
}

export function ClayModal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="clay-card w-full max-w-lg space-y-4 p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-foreground">{title}</h2>
            {description && <p className="mt-1 text-xs text-muted-foreground">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="clay-btn rounded-xl p-1.5 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div>{children}</div>
        {footer && <div className="flex justify-end gap-2 pt-2">{footer}</div>}
      </div>
    </div>
  );
}

export function ClayDropdown({
  label,
  items,
}: {
  label: ReactNode;
  items: { id: string; label: string; onClick: () => void; danger?: boolean }[];
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="clay-btn inline-flex items-center gap-1.5 bg-card px-3 py-1.5 text-xs font-medium text-foreground"
      >
        {label}
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
      </button>
      {open && (
        <div className="clay-card absolute right-0 z-40 mt-2 min-w-[180px] p-1.5">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                setOpen(false);
                item.onClick();
              }}
              className={`w-full rounded-xl px-3 py-2 text-left text-xs font-medium transition-colors hover:bg-muted/70 ${
                item.danger ? "text-[#DF6F79]" : "text-foreground"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ClayTooltip({
  content,
  children,
}: {
  content: string;
  children: ReactNode;
}) {
  return (
    <span className="group relative inline-flex">
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-40 mb-2 -translate-x-1/2 whitespace-nowrap rounded-xl bg-foreground px-2.5 py-1 text-[11px] font-medium text-background opacity-0 shadow-clay-sm transition-opacity group-hover:opacity-100"
      >
        {content}
      </span>
    </span>
  );
}

export function ClayTable({
  headers,
  children,
  className = "",
}: {
  headers: string[];
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`clay-card overflow-hidden p-0 ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/60 bg-muted/45 text-xs font-medium text-muted-foreground">
            <tr>
              {headers.map((h) => (
                <th key={h} className="px-4 py-3">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">{children}</tbody>
        </table>
      </div>
    </div>
  );
}
