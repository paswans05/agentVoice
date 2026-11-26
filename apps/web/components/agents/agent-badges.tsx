import type { AgentStatus, AgentType } from "@agentvoice/shared-types";
import { Bot, Briefcase, Calendar, Headphones, Target, Sparkles } from "lucide-react";
import type { ComponentType } from "react";

export const AGENT_STATUS_STYLES: Record<AgentStatus, string> = {
  DRAFT: "bg-slate-500/15 text-slate-600 dark:text-slate-300 border-slate-500/30",
  ACTIVE: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
  INACTIVE: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
};

export const AGENT_TYPE_LABELS: Record<AgentType, string> = {
  SALES: "Sales",
  CUSTOMER_SUPPORT: "Customer Support",
  LEAD_QUALIFICATION: "Lead Qualification",
  APPOINTMENT_BOOKING: "Appointment Booking",
  GENERAL_ASSISTANT: "General Assistant",
  CUSTOM: "Custom",
};

const AVATAR_ICONS: Record<string, ComponentType<{ className?: string }>> = {
  bot: Bot,
  briefcase: Briefcase,
  headphones: Headphones,
  target: Target,
  calendar: Calendar,
  sparkles: Sparkles,
};

export function AgentAvatar({ avatar, className = "h-5 w-5" }: { avatar: string; className?: string }) {
  const Icon = AVATAR_ICONS[avatar] ?? Bot;
  return <Icon className={className} />;
}

export function AgentStatusBadge({ status }: { status: AgentStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${AGENT_STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

export function formatAgentDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}
