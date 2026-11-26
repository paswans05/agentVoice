export type StatusTone = "healthy" | "degraded" | "unavailable" | "neutral";

export const STATUS_TONE_CLASSES: Record<StatusTone, string> = {
  healthy: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
  degraded: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
  unavailable: "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30",
  neutral: "bg-slate-500/15 text-slate-600 dark:text-slate-400 border-slate-500/30",
};
