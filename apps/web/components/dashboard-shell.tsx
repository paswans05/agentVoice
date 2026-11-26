"use client";

import { APP_CONFIG, SIDEBAR_NAV_ITEMS } from "@agentvoice/config";
import { STATUS_TONE_CLASSES } from "@agentvoice/ui";
import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
  Cpu,
  History,
  LayoutDashboard,
  Megaphone,
  Menu,
  Mic,
  PhoneCall,
  PhoneForwarded,
  Settings,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ComponentType, type ReactNode } from "react";
import { useBackendHealth } from "@/hooks/use-health";
import { BrandLogo } from "./brand-logo";
import { ThemeToggle } from "./theme-toggle";

const NAV_ICONS: Record<string, ComponentType<{ className?: string }>> = {
  overview: LayoutDashboard,
  agents: Bot,
  models: Cpu,
  playground: Mic,
  "knowledge-base": BookOpen,
  leads: Users,
  campaigns: Megaphone,
  "live-calls": PhoneCall,
  "call-history": History,
  analytics: BarChart3,
  telephony: PhoneForwarded,
  settings: Settings,
};

export function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { data: health, isLoading, isError } = useBackendHealth();

  const statusTone = isLoading
    ? "neutral"
    : isError || !health
      ? "unavailable"
      : health.status === "healthy"
        ? "healthy"
        : "degraded";

  const statusLabel = isLoading
    ? "Connecting..."
    : isError || !health
      ? "API Offline"
      : `API ${health.status}`;

  const renderNavLinks = () => (
    <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Sidebar navigation">
      {SIDEBAR_NAV_ITEMS.map((item) => {
        const Icon = NAV_ICONS[item.id] ?? Activity;
        const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

        return (
          <Link
            key={item.id}
            href={item.href}
            onClick={() => setMobileOpen(false)}
            className={`group flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <span className="flex items-center gap-3">
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.label}</span>
            </span>
            {item.status === "planned" && (
              <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                P{item.phase}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      {/* Desktop Sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-card lg:flex">
        <div className="flex h-16 items-center border-b border-border px-5">
          <Link href="/" className="hover:opacity-90 transition-opacity">
            <BrandLogo showSubtitle />
          </Link>
        </div>
        {renderNavLinks()}
        <div className="border-t border-border p-4 text-xs text-muted-foreground">
          <div>v{APP_CONFIG.version} · Local-First</div>
        </div>
      </aside>

      {/* Mobile Sidebar Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="fixed inset-0 bg-black/50"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <aside className="relative z-10 flex w-64 flex-col border-r border-border bg-card">
            <div className="flex h-16 items-center justify-between border-b border-border px-5">
              <Link href="/" onClick={() => setMobileOpen(false)}>
                <BrandLogo />
              </Link>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation menu"
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            {renderNavLinks()}
          </aside>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col min-w-0">
        <header className="flex h-16 items-center justify-between border-b border-border bg-card px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation menu"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-foreground hover:bg-muted lg:hidden"
            >
              <Menu className="h-4 w-4" />
            </button>
            <p className="hidden text-xs text-muted-foreground sm:block">{APP_CONFIG.tagline}</p>
          </div>

          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium capitalize ${STATUS_TONE_CLASSES[statusTone]}`}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-current" />
              {statusLabel}
            </span>
            <ThemeToggle />
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
