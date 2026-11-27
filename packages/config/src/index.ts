export const APP_CONFIG = {
  name: "agentVoice",
  tagline: "Your AI. Your Voice. Your Infrastructure.",
  version: "0.1.0",
  defaultApiUrl: "http://localhost:8000",
} as const;

export interface NavItemConfig {
  id: string;
  label: string;
  href: string;
  phase: number;
  status: "active" | "planned";
  description: string;
}

export const SIDEBAR_NAV_ITEMS: NavItemConfig[] = [
  {
    id: "overview",
    label: "Overview",
    href: "/",
    phase: 1,
    status: "active",
    description: "System health, runtime status, and platform overview",
  },
  {
    id: "agents",
    label: "AI Agents",
    href: "/agents",
    phase: 2,
    status: "active",
    description: "Create and configure local voice AI agents",
  },
  {
    id: "models",
    label: "Model Manager",
    href: "/models",
    phase: 3,
    status: "active",
    description: "Manage local LLM, STT, and TTS models",
  },
  {
    id: "playground",
    label: "Voice Playground",
    href: "/playground",
    phase: 4,
    status: "active",
    description: "Real-time browser microphone voice testing",
  },
  {
    id: "knowledge-base",
    label: "Knowledge Base",
    href: "/knowledge-base",
    phase: 5,
    status: "active",
    description: "Upload documents and manage local RAG knowledge bases",
  },
  {
    id: "leads",
    label: "Leads",
    href: "/leads",
    phase: 7,
    status: "active",
    description: "Manage contacts, CSV import/export, and consent",
  },
  {
    id: "campaigns",
    label: "Campaigns",
    href: "/campaigns",
    phase: 8,
    status: "active",
    description: "Outbound calling workflows and schedules",
  },
  {
    id: "live-calls",
    label: "Live Calls",
    href: "/live-calls",
    phase: 9,
    status: "planned",
    description: "Monitor active calls and live transcripts",
  },
  {
    id: "call-history",
    label: "Call History",
    href: "/call-history",
    phase: 8,
    status: "active",
    description: "Review past call transcripts and summaries",
  },
  {
    id: "analytics",
    label: "Analytics",
    href: "/analytics",
    phase: 8,
    status: "active",
    description: "Call performance, conversion, and agent metrics",
  },
  {
    id: "telephony",
    label: "Telephony",
    href: "/telephony",
    phase: 9,
    status: "planned",
    description: "Authorized SIP, Asterisk, and GSM gateway setup",
  },
  {
    id: "settings",
    label: "Settings",
    href: "/settings",
    phase: 1,
    status: "active",
    description: "Storage, theme, runtime, and system configuration",
  },
];
