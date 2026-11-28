"use client";

import { APP_CONFIG, SIDEBAR_NAV_ITEMS } from "@agentvoice/config";
import { STATUS_TONE_CLASSES, type StatusTone } from "@agentvoice/ui";
import {
  Activity,
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  ChevronLeft,
  ChevronRight,
  Cpu,
  History,
  LayoutDashboard,
  Megaphone,
  Menu,
  Mic,
  PhoneCall,
  PhoneForwarded,
  Search,
  Settings,
  User,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ComponentType } from "react";
import { BrandLogo } from "../brand-logo";
import { ThemeToggle } from "../theme-toggle";
import { ClayDropdown } from "./navigation";

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

export function ClaySidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}) {
  const pathname = usePathname();

  const renderLinks = (isMobile = false) => (
    <nav className="flex-1 space-y-1.5 overflow-y-auto px-3 py-4" aria-label="Sidebar navigation">
      {SIDEBAR_NAV_ITEMS.map((item) => {
        const Icon = NAV_ICONS[item.id] ?? Activity;
        const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

        return (
          <Link
            key={item.id}
            href={item.href}
            onClick={onCloseMobile}
            title={collapsed && !isMobile ? item.label : undefined}
            className={`group flex items-center justify-between rounded-2xl px-3 py-2.5 text-sm font-medium transition-all ${
              isActive
                ? "bg-card text-primary shadow-clay-sm border border-border/60"
                : "text-muted-foreground hover:bg-card/60 hover:text-foreground"
            }`}
          >
            <span className="flex items-center gap-3 min-w-0">
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition-colors ${
                  isActive
                    ? "bg-primary/15 text-primary shadow-clay-inset"
                    : "bg-muted/60 text-muted-foreground group-hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
              </span>
              {(!collapsed || isMobile) && <span className="truncate">{item.label}</span>}
            </span>
          </Link>
        );
      })}
    </nav>
  );

  return (
    <>
      {/* Desktop Collapsible Clay Sidebar */}
      <aside
        className={`hidden shrink-0 flex-col p-3 transition-all duration-200 lg:flex ${
          collapsed ? "w-24" : "w-68"
        }`}
      >
        <div className="clay-card flex h-full flex-col overflow-hidden p-0">
          <div className="flex h-16 items-center justify-between border-b border-border/50 px-4">
            {!collapsed && (
              <Link href="/" className="transition-opacity hover:opacity-90">
                <BrandLogo showSubtitle />
              </Link>
            )}
            <button
              type="button"
              onClick={onToggleCollapse}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              className="clay-btn ml-auto flex h-8 w-8 items-center justify-center rounded-xl bg-card text-muted-foreground hover:text-foreground"
            >
              {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </button>
          </div>

          {renderLinks(false)}

          <div className="border-t border-border/50 px-4 py-3 text-[11px] text-muted-foreground">
            {collapsed ? `v${APP_CONFIG.version}` : `v${APP_CONFIG.version} · Local-First Clay`}
          </div>
        </div>
      </aside>

      {/* Mobile Clay Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="fixed inset-0 bg-black/45 backdrop-blur-xs"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <aside className="clay-card relative z-10 m-3 flex w-72 flex-col overflow-hidden p-0">
            <div className="flex h-16 items-center justify-between border-b border-border/50 px-4">
              <Link href="/" onClick={onCloseMobile}>
                <BrandLogo />
              </Link>
              <button
                type="button"
                onClick={onCloseMobile}
                aria-label="Close navigation menu"
                className="clay-btn rounded-xl p-1.5 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            {renderLinks(true)}
          </aside>
        </div>
      )}
    </>
  );
}

export function ClayNavbar({
  onOpenMobile,
  statusTone,
  statusLabel,
}: {
  onOpenMobile: () => void;
  statusTone: StatusTone;
  statusLabel: string;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [showAlerts, setShowAlerts] = useState(false);

  const segments = pathname.split("/").filter(Boolean);
  const currentNav = SIDEBAR_NAV_ITEMS.find((item) =>
    item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
  );

  const handleQuickJump = (e: React.FormEvent) => {
    e.preventDefault();
    const q = search.trim().toLowerCase();
    if (!q) return;
    const match = SIDEBAR_NAV_ITEMS.find(
      (i) => i.label.toLowerCase().includes(q) || i.id.toLowerCase().includes(q),
    );
    if (match) {
      setSearch("");
      router.push(match.href);
    }
  };

  return (
    <header className="px-4 pt-3 sm:px-6 lg:px-8">
      <div className="clay-card flex flex-wrap items-center justify-between gap-3 rounded-2xl px-4 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={onOpenMobile}
            aria-label="Open navigation menu"
            className="clay-btn inline-flex h-9 w-9 items-center justify-center rounded-xl bg-card text-foreground lg:hidden"
          >
            <Menu className="h-4 w-4" />
          </button>

          {/* Breadcrumbs */}
          <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Link href="/" className="font-medium hover:text-foreground">
              AgentVoice
            </Link>
            <span>/</span>
            <span className="font-semibold text-foreground truncate">
              {currentNav?.label ?? (segments[0] ? segments[0].replace(/-/g, " ") : "Overview")}
            </span>
          </nav>
        </div>

        {/* Clay Search & Controls */}
        <div className="flex items-center gap-2.5">
          <form onSubmit={handleQuickJump} className="relative hidden md:block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Jump to module..."
              aria-label="Jump to module"
              className="clay-inset w-48 rounded-xl py-1.5 pl-8 pr-3 text-xs text-foreground placeholder:text-muted-foreground/75 focus:outline-none"
            />
          </form>

          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium capitalize ${STATUS_TONE_CLASSES[statusTone]}`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {statusLabel}
          </span>

          <div className="relative">
            <button
              type="button"
              onClick={() => setShowAlerts((v) => !v)}
              aria-label="Notifications"
              className="clay-btn inline-flex h-9 w-9 items-center justify-center rounded-xl bg-card text-foreground"
            >
              <Bell className="h-4 w-4" />
            </button>
            {showAlerts && (
              <div className="clay-card absolute right-0 z-40 mt-2 w-64 space-y-2 p-3 text-xs">
                <div className="font-semibold text-foreground">System Notifications</div>
                <p className="text-muted-foreground">
                  Platform status: <span className="font-medium text-foreground">{statusLabel}</span>
                </p>
                <Link
                  href="/telephony/dialer"
                  onClick={() => setShowAlerts(false)}
                  className="block rounded-xl bg-muted/60 px-2.5 py-1.5 text-primary hover:bg-muted"
                >
                  Open Internal WebRTC Dialer →
                </Link>
              </div>
            )}
          </div>

          <ThemeToggle />

          <ClayDropdown
            label={
              <span className="flex items-center gap-1.5">
                <User className="h-3.5 w-3.5 text-primary" />
                <span className="hidden sm:inline">Operator</span>
              </span>
            }
            items={[
              { id: "settings", label: "Platform Settings", onClick: () => router.push("/settings") },
              { id: "telephony", label: "Telephony Setup", onClick: () => router.push("/telephony") },
              { id: "testing", label: "Testing Lab", onClick: () => router.push("/testing-lab") },
            ]}
          />
        </div>
      </div>
    </header>
  );
}
