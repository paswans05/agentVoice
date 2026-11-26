"use client";

import type {
  Agent,
  AgentCreatePayload,
  AgentTemplate,
  AgentType,
  LanguageResponseMode,
  PersonalityTone,
  SupportedLocale,
} from "@agentvoice/shared-types";
import { Check, ChevronLeft, ChevronRight, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AGENT_TYPE_LABELS } from "./agent-badges";

const STEPS = [
  { id: "basic", label: "Basic Info" },
  { id: "personality", label: "Personality" },
  { id: "instructions", label: "Instructions" },
  { id: "language", label: "Language" },
  { id: "voice", label: "Voice" },
  { id: "review", label: "Review" },
] as const;

const TONES: PersonalityTone[] = [
  "FRIENDLY",
  "PROFESSIONAL",
  "FORMAL",
  "CASUAL",
  "CONFIDENT",
  "EMPATHETIC",
  "CUSTOM",
];

const AGENT_TYPES: AgentType[] = [
  "SALES",
  "CUSTOMER_SUPPORT",
  "LEAD_QUALIFICATION",
  "APPOINTMENT_BOOKING",
  "GENERAL_ASSISTANT",
  "CUSTOM",
];

const AVATARS = ["bot", "briefcase", "headphones", "target", "calendar", "sparkles"];

interface AgentFormProps {
  mode: "create" | "edit";
  initialAgent?: Agent;
  templates?: AgentTemplate[];
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (payload: AgentCreatePayload, activateAfterSave: boolean) => Promise<void>;
  onCancel: () => void;
}

export function AgentForm({
  mode,
  initialAgent,
  templates = [],
  isSubmitting,
  errorMessage,
  onSubmit,
  onCancel,
}: AgentFormProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");

  const [name, setName] = useState(initialAgent?.name ?? "");
  const [description, setDescription] = useState(initialAgent?.description ?? "");
  const [avatar, setAvatar] = useState(initialAgent?.avatar ?? "bot");
  const [type, setType] = useState<AgentType>(initialAgent?.type ?? "GENERAL_ASSISTANT");

  const [tone, setTone] = useState<PersonalityTone>(initialAgent?.personality.tone ?? "FRIENDLY");
  const [traitsInput, setTraitsInput] = useState(
    (initialAgent?.personality.traits ?? ["helpful", "polite"]).join(", "),
  );
  const [customPersonality, setCustomPersonality] = useState(
    initialAgent?.personality.custom_instructions ?? "",
  );

  const [systemPrompt, setSystemPrompt] = useState(initialAgent?.instructions.system_prompt ?? "");
  const [greeting, setGreeting] = useState(initialAgent?.instructions.greeting ?? "");
  const [rulesInput, setRulesInput] = useState(
    (initialAgent?.instructions.additional_rules ?? []).join("\n"),
  );

  const [primaryLanguage, setPrimaryLanguage] = useState<SupportedLocale>(
    initialAgent?.language.primary_language ?? "en-IN",
  );
  const [supportedLanguages, setSupportedLanguages] = useState<SupportedLocale[]>(
    initialAgent?.language.supported_languages ?? ["en-IN", "hi-IN"],
  );
  const [hinglishEnabled, setHinglishEnabled] = useState(
    initialAgent?.language.hinglish_enabled ?? true,
  );
  const [responseMode, setResponseMode] = useState<LanguageResponseMode>(
    initialAgent?.language.response_mode ?? "AUTO",
  );

  const [voiceProvider, setVoiceProvider] = useState(initialAgent?.voice.provider ?? "piper");
  const [voiceId, setVoiceId] = useState(initialAgent?.voice.voice_id ?? "default");
  const [speed, setSpeed] = useState(initialAgent?.voice.speed ?? 1.0);
  const [pitch, setPitch] = useState(initialAgent?.voice.pitch ?? 1.0);

  const [validationError, setValidationError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  // Warn before leaving with unsaved changes
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const markDirty = () => {
    if (!dirty) setDirty(true);
  };

  const applyTemplate = (templateId: string) => {
    setSelectedTemplateId(templateId);
    const tpl = templates.find((t) => t.id === templateId);
    if (!tpl) return;
    setName(tpl.name);
    setDescription(tpl.description);
    setAvatar(tpl.avatar);
    setType(tpl.type);
    setTone(tpl.personality.tone);
    setTraitsInput(tpl.personality.traits.join(", "));
    setCustomPersonality(tpl.personality.custom_instructions);
    setSystemPrompt(tpl.instructions.system_prompt);
    setGreeting(tpl.instructions.greeting);
    setRulesInput(tpl.instructions.additional_rules.join("\n"));
    setPrimaryLanguage(tpl.language.primary_language);
    setSupportedLanguages(tpl.language.supported_languages);
    setHinglishEnabled(tpl.language.hinglish_enabled);
    setResponseMode(tpl.language.response_mode);
    setVoiceProvider(tpl.voice.provider);
    setVoiceId(tpl.voice.voice_id);
    setSpeed(tpl.voice.speed);
    setPitch(tpl.voice.pitch);
    setDirty(true);
  };

  const toggleSupportedLocale = (locale: SupportedLocale) => {
    markDirty();
    setSupportedLanguages((prev) => {
      if (prev.includes(locale)) {
        if (locale === primaryLanguage) return prev;
        const next = prev.filter((item) => item !== locale);
        return next.length > 0 ? next : [primaryLanguage];
      }
      return [...prev, locale];
    });
  };

  const parsedTraits = useMemo(
    () =>
      traitsInput
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    [traitsInput],
  );

  const parsedRules = useMemo(
    () =>
      rulesInput
        .split("\n")
        .map((r) => r.trim())
        .filter(Boolean),
    [rulesInput],
  );

  const buildPayload = (): AgentCreatePayload => ({
    name: name.trim(),
    description: description.trim(),
    avatar,
    type,
    template_id: mode === "create" && selectedTemplateId ? selectedTemplateId : undefined,
    personality: {
      tone,
      traits: parsedTraits,
      custom_instructions: customPersonality.trim(),
    },
    instructions: {
      system_prompt: systemPrompt.trim(),
      greeting: greeting.trim(),
      additional_rules: parsedRules,
    },
    language: {
      primary_language: primaryLanguage,
      supported_languages: supportedLanguages.includes(primaryLanguage)
        ? supportedLanguages
        : [primaryLanguage, ...supportedLanguages],
      hinglish_enabled: hinglishEnabled,
      response_mode: responseMode,
    },
    voice: {
      provider: voiceProvider.trim() || "piper",
      voice_id: voiceId.trim() || "default",
      speed,
      pitch,
    },
  });

  const validateForSubmit = (activateAfterSave: boolean): string | null => {
    if (name.trim().length < 2 || name.trim().length > 80) {
      return "Agent name must be between 2 and 80 characters.";
    }
    if (description.trim().length > 500) {
      return "Description must be at most 500 characters.";
    }
    if (activateAfterSave && !systemPrompt.trim()) {
      return "System prompt is required before activating an agent.";
    }
    if (speed < 0.5 || speed > 2.0 || pitch < 0.5 || pitch > 2.0) {
      return "Voice speed and pitch must be between 0.5 and 2.0.";
    }
    return null;
  };

  const handleSave = async (activateAfterSave: boolean) => {
    const err = validateForSubmit(activateAfterSave);
    if (err) {
      setValidationError(err);
      return;
    }
    setValidationError(null);
    setDirty(false);
    await onSubmit(buildPayload(), activateAfterSave);
  };

  const currentStep = STEPS[stepIndex];

  return (
    <div className="space-y-6">
      {/* Stepper */}
      <nav aria-label="Agent configuration steps" className="grid grid-cols-3 gap-2 sm:grid-cols-6">
        {STEPS.map((step, idx) => {
          const isCurrent = idx === stepIndex;
          const isCompleted = idx < stepIndex;
          return (
            <button
              key={step.id}
              type="button"
              onClick={() => setStepIndex(idx)}
              className={`flex items-center justify-center gap-1.5 rounded-lg border px-2.5 py-2 text-xs font-medium transition-colors ${
                isCurrent
                  ? "border-primary bg-primary/10 text-primary"
                  : isCompleted
                    ? "border-border bg-card text-foreground hover:bg-muted"
                    : "border-border bg-card text-muted-foreground hover:bg-muted"
              }`}
            >
              {isCompleted && <Check className="h-3.5 w-3.5 text-emerald-500" />}
              <span>{step.label}</span>
            </button>
          );
        })}
      </nav>

      {(validationError || errorMessage) && (
        <div
          role="alert"
          className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-700 dark:text-rose-300"
        >
          {validationError ?? errorMessage}
        </div>
      )}

      <div className="rounded-xl border border-border bg-card p-6 space-y-5">
        {currentStep.id === "basic" && (
          <div className="space-y-4">
            {mode === "create" && templates.length > 0 && (
              <div className="rounded-lg border border-border bg-muted/40 p-4">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <span>Start from a Starter Template (Optional)</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Pre-fill configuration with an editable template. All new agents start as DRAFT.
                </p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {templates.map((tpl) => (
                    <button
                      key={tpl.id}
                      type="button"
                      onClick={() => applyTemplate(tpl.id)}
                      className={`rounded-lg border p-3 text-left text-xs transition-colors ${
                        selectedTemplateId === tpl.id
                          ? "border-primary bg-primary/10"
                          : "border-border bg-card hover:bg-muted"
                      }`}
                    >
                      <div className="font-semibold">{tpl.name}</div>
                      <div className="mt-0.5 text-muted-foreground line-clamp-2">
                        {tpl.description}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div>
              <label htmlFor="agent-name" className="block text-sm font-medium">
                Agent Name <span className="text-rose-500">*</span>
              </label>
              <input
                id="agent-name"
                type="text"
                value={name}
                onChange={(e) => {
                  markDirty();
                  setName(e.target.value);
                }}
                placeholder="e.g., Asha Sales Assistant"
                maxLength={80}
                className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="agent-description" className="block text-sm font-medium">
                Description
              </label>
              <textarea
                id="agent-description"
                rows={3}
                value={description}
                onChange={(e) => {
                  markDirty();
                  setDescription(e.target.value);
                }}
                placeholder="Briefly describe what this agent handles..."
                maxLength={500}
                className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="agent-type" className="block text-sm font-medium">
                  Agent Type
                </label>
                <select
                  id="agent-type"
                  value={type}
                  onChange={(e) => {
                    markDirty();
                    setType(e.target.value as AgentType);
                  }}
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
                >
                  {AGENT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {AGENT_TYPE_LABELS[t]}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="agent-avatar" className="block text-sm font-medium">
                  Avatar Icon
                </label>
                <select
                  id="agent-avatar"
                  value={avatar}
                  onChange={(e) => {
                    markDirty();
                    setAvatar(e.target.value);
                  }}
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm capitalize focus:border-primary focus:outline-none"
                >
                  {AVATARS.map((av) => (
                    <option key={av} value={av}>
                      {av}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {currentStep.id === "personality" && (
          <div className="space-y-4">
            <div>
              <label htmlFor="personality-tone" className="block text-sm font-medium">
                Conversational Tone
              </label>
              <select
                id="personality-tone"
                value={tone}
                onChange={(e) => {
                  markDirty();
                  setTone(e.target.value as PersonalityTone);
                }}
                className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              >
                {TONES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="personality-traits" className="block text-sm font-medium">
                Personality Traits (comma-separated)
              </label>
              <input
                id="personality-traits"
                type="text"
                value={traitsInput}
                onChange={(e) => {
                  markDirty();
                  setTraitsInput(e.target.value);
                }}
                placeholder="helpful, polite, consultative"
                className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="personality-custom" className="block text-sm font-medium">
                Custom Personality Notes
              </label>
              <textarea
                id="personality-custom"
                rows={4}
                value={customPersonality}
                onChange={(e) => {
                  markDirty();
                  setCustomPersonality(e.target.value);
                }}
                placeholder="Describe style nuances, pacing, or politeness guidelines..."
                maxLength={1500}
                className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              />
            </div>
          </div>
        )}

        {currentStep.id === "instructions" && (
          <div className="space-y-4">
            <div>
              <label htmlFor="system-prompt" className="block text-sm font-medium">
                System Prompt
              </label>
              <textarea
                id="system-prompt"
                rows={5}
                value={systemPrompt}
                onChange={(e) => {
                  markDirty();
                  setSystemPrompt(e.target.value);
                }}
                placeholder="You are a friendly assistant for..."
                maxLength={8000}
                className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Required before activating the agent. Stored as configuration only.
              </p>
            </div>

            <div>
              <label htmlFor="greeting" className="block text-sm font-medium">
                Opening Greeting
              </label>
              <textarea
                id="greeting"
                rows={2}
                value={greeting}
                onChange={(e) => {
                  markDirty();
                  setGreeting(e.target.value);
                }}
                placeholder="Namaste! Main aapki AI assistant bol rahi hoon..."
                maxLength={1000}
                className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="additional-rules" className="block text-sm font-medium">
                Additional Rules (one per line)
              </label>
              <textarea
                id="additional-rules"
                rows={4}
                value={rulesInput}
                onChange={(e) => {
                  markDirty();
                  setRulesInput(e.target.value);
                }}
                placeholder={"Never invent pricing or discounts.\nOffer human handoff if requested."}
                className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              />
            </div>
          </div>
        )}

        {currentStep.id === "language" && (
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="primary-language" className="block text-sm font-medium">
                  Primary Language
                </label>
                <select
                  id="primary-language"
                  value={primaryLanguage}
                  onChange={(e) => {
                    const next = e.target.value as SupportedLocale;
                    markDirty();
                    setPrimaryLanguage(next);
                    if (!supportedLanguages.includes(next)) {
                      setSupportedLanguages((prev) => [next, ...prev]);
                    }
                  }}
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
                >
                  <option value="en-IN">English (en-IN)</option>
                  <option value="hi-IN">Hindi (hi-IN)</option>
                </select>
              </div>

              <div>
                <label htmlFor="response-mode" className="block text-sm font-medium">
                  Response Mode
                </label>
                <select
                  id="response-mode"
                  value={responseMode}
                  onChange={(e) => {
                    markDirty();
                    setResponseMode(e.target.value as LanguageResponseMode);
                  }}
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
                >
                  <option value="AUTO">AUTO (Match caller language)</option>
                  <option value="PRIMARY">PRIMARY (Prefer primary language)</option>
                  <option value="FIXED">FIXED (Strict primary language)</option>
                </select>
              </div>
            </div>

            <div>
              <span className="block text-sm font-medium">Supported Languages</span>
              <div className="mt-2 flex flex-wrap gap-3">
                {(["en-IN", "hi-IN"] as SupportedLocale[]).map((loc) => (
                  <label key={loc} className="inline-flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={supportedLanguages.includes(loc)}
                      onChange={() => toggleSupportedLocale(loc)}
                      disabled={loc === primaryLanguage}
                      className="rounded border-border"
                    />
                    <span>{loc === "hi-IN" ? "Hindi (hi-IN)" : "English (en-IN)"}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-border bg-muted/40 p-4">
              <label className="flex items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={hinglishEnabled}
                  onChange={(e) => {
                    markDirty();
                    setHinglishEnabled(e.target.checked);
                  }}
                  className="mt-1 rounded border-border"
                />
                <span>
                  <span className="font-medium">Enable Hinglish (Mixed Hindi-English) Mode</span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">
                    Configures conversational response behavior for natural Hindi + English mixing
                    rather than treating Hinglish as a separate formal locale.
                  </span>
                </span>
              </label>
            </div>
          </div>
        )}

        {currentStep.id === "voice" && (
          <div className="space-y-4">
            <p className="text-xs text-muted-foreground">
              Save your preferred local TTS provider and voice settings now. Preferences are stored
              even before a local TTS engine is installed in Phase 4.
            </p>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="voice-provider" className="block text-sm font-medium">
                  TTS Provider
                </label>
                <select
                  id="voice-provider"
                  value={voiceProvider}
                  onChange={(e) => {
                    markDirty();
                    setVoiceProvider(e.target.value);
                  }}
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
                >
                  <option value="piper">Piper (Local)</option>
                  <option value="custom">Custom Local Provider</option>
                </select>
              </div>

              <div>
                <label htmlFor="voice-id" className="block text-sm font-medium">
                  Voice ID
                </label>
                <input
                  id="voice-id"
                  type="text"
                  value={voiceId}
                  onChange={(e) => {
                    markDirty();
                    setVoiceId(e.target.value);
                  }}
                  placeholder="default"
                  maxLength={120}
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="voice-speed" className="block text-sm font-medium">
                  Speaking Speed ({speed.toFixed(2)}x)
                </label>
                <input
                  id="voice-speed"
                  type="range"
                  min={0.5}
                  max={2.0}
                  step={0.05}
                  value={speed}
                  onChange={(e) => {
                    markDirty();
                    setSpeed(Number(e.target.value));
                  }}
                  className="mt-2 w-full"
                />
              </div>

              <div>
                <label htmlFor="voice-pitch" className="block text-sm font-medium">
                  Pitch ({pitch.toFixed(2)})
                </label>
                <input
                  id="voice-pitch"
                  type="range"
                  min={0.5}
                  max={2.0}
                  step={0.05}
                  value={pitch}
                  onChange={(e) => {
                    markDirty();
                    setPitch(Number(e.target.value));
                  }}
                  className="mt-2 w-full"
                />
              </div>
            </div>
          </div>
        )}

        {currentStep.id === "review" && (
          <div className="space-y-4 text-sm">
            <h2 className="text-base font-semibold">Configuration Summary</h2>
            <dl className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border p-3">
                <dt className="text-xs text-muted-foreground">Name &amp; Type</dt>
                <dd className="mt-1 font-medium">
                  {name || "—"} · {AGENT_TYPE_LABELS[type]}
                </dd>
              </div>
              <div className="rounded-lg border border-border p-3">
                <dt className="text-xs text-muted-foreground">Personality</dt>
                <dd className="mt-1 font-medium">
                  {tone} {parsedTraits.length > 0 ? `(${parsedTraits.join(", ")})` : ""}
                </dd>
              </div>
              <div className="rounded-lg border border-border p-3">
                <dt className="text-xs text-muted-foreground">Language</dt>
                <dd className="mt-1 font-medium">
                  {primaryLanguage} · {responseMode}
                  {hinglishEnabled ? " · Hinglish" : ""}
                </dd>
              </div>
              <div className="rounded-lg border border-border p-3">
                <dt className="text-xs text-muted-foreground">Voice Preference</dt>
                <dd className="mt-1 font-medium">
                  {voiceProvider} / {voiceId} ({speed.toFixed(2)}x)
                </dd>
              </div>
            </dl>
            <div className="rounded-lg border border-border p-3">
              <div className="text-xs text-muted-foreground">System Prompt</div>
              <p className="mt-1 whitespace-pre-wrap text-xs">
                {systemPrompt.trim() || "No system prompt configured (required for activation)."}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Footer Navigation & Submit */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted"
          >
            Cancel
          </button>
          {stepIndex > 0 && (
            <button
              type="button"
              onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-3.5 py-2 text-sm font-medium hover:bg-muted"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {stepIndex < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={() => setStepIndex((i) => Math.min(STEPS.length - 1, i + 1))}
              className="inline-flex items-center gap-1 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          ) : (
            <>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => void handleSave(false)}
                className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
              >
                {isSubmitting ? "Saving..." : mode === "create" ? "Save as Draft" : "Save Changes"}
              </button>
              {mode === "create" && (
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => void handleSave(true)}
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
                >
                  {isSubmitting ? "Saving..." : "Save and Activate"}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
