export type StatusTone = "healthy" | "degraded" | "unavailable" | "neutral";

export const STATUS_TONE_CLASSES: Record<StatusTone, string> = {
  healthy:
    "bg-[#42A889]/15 text-[#2C8469] dark:text-[#66CCA9] border-[#42A889]/35 shadow-sm",
  degraded:
    "bg-[#E5A64B]/18 text-[#A66E1B] dark:text-[#F2BE6B] border-[#E5A64B]/35 shadow-sm",
  unavailable:
    "bg-[#DF6F79]/16 text-[#B64450] dark:text-[#F08C95] border-[#DF6F79]/35 shadow-sm",
  neutral:
    "bg-muted/80 text-muted-foreground border-border/70 shadow-sm",
};
