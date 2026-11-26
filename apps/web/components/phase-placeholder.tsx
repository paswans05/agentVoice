import { Clock } from "lucide-react";

interface PhasePlaceholderProps {
  title: string;
  description: string;
  phase: number;
}

export function PhasePlaceholder({ title, description, phase }: PhasePlaceholderProps) {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>

      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Clock className="h-5 w-5" />
          </div>
          <div className="space-y-1.5">
            <div className="inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              Scheduled for Phase {phase}
            </div>
            <h2 className="text-base font-medium">Module not yet enabled</h2>
            <p className="text-sm text-muted-foreground">
              agentVoice is currently on <strong>Phase 1 — Foundation</strong>. This section is
              part of the verified roadmap and will be activated in Phase {phase} once its backend
              providers and tests are implemented.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
