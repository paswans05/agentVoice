"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type {
  Agent,
  CustomerPersona,
  TestingOverviewStats,
  TestRun,
  TestScenario,
} from "@agentvoice/shared-types";
import {
  Activity,
  Bot,
  CheckCircle2,
  Cpu,
  Download,
  FlaskConical,
  Mic,
  Play,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  Trash2,
} from "lucide-react";

import {
  createTestingScenario,
  deleteTestingScenario,
  deleteTestRun,
  fetchAgents,
  fetchTestingPersonas,
  fetchTestingScenarios,
  fetchTestingStatus,
  fetchTestRuns,
  getTestReportExportUrl,
  rerunFailedTest,
  runFailureRecoverySuiteTest,
  runKbSuiteTest,
  runPerformanceSuiteTest,
  runTelephonySuiteTest,
  runTestingAssistant,
  runTestSimulation,
} from "@/lib/api-client";

type LabTab =
  | "overview"
  | "simulator"
  | "scenarios"
  | "live"
  | "suites"
  | "reports"
  | "assistant";

export default function TestingLabPage() {
  const [tab, setTab] = useState<LabTab>("overview");
  const [stats, setStats] = useState<TestingOverviewStats | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [personas, setPersonas] = useState<CustomerPersona[]>([]);
  const [scenarios, setScenarios] = useState<TestScenario[]>([]);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [selectedPersonaId, setSelectedPersonaId] = useState("interested");
  const [selectedScenarioId, setSelectedScenarioId] = useState("");
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [maxTurns, setMaxTurns] = useState(4);
  const [activeRun, setActiveRun] = useState<TestRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Scenario Builder state
  const [scenName, setScenName] = useState("");
  const [scenObjective, setScenObjective] = useState("");
  const [scenPersona, setScenPersona] = useState("interested");

  // Suites state
  const [suiteOutput, setSuiteOutput] = useState<Record<string, unknown> | null>(null);

  // Assistant state
  const [assistantPrompt, setAssistantPrompt] = useState(
    "Test my sales agent like you are a real customer. Check pricing questions, objections, Hindi conversations, interruptions and demo booking.",
  );
  const [assistantResult, setAssistantResult] = useState<Record<string, unknown> | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [st, ags, pers, scens, rns] = await Promise.all([
        fetchTestingStatus(),
        fetchAgents(),
        fetchTestingPersonas(),
        fetchTestingScenarios(),
        fetchTestRuns(),
      ]);
      setStats(st);
      setAgents(ags);
      setPersonas(pers);
      setScenarios(scens);
      setRuns(rns);
      if (ags.length > 0) {
        setSelectedAgentId((prev) => prev || ags[0].id);
      }
      setErrorMsg(null);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load Testing Lab.");
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const handleRunSimulation = async () => {
    if (!selectedAgentId) return;
    setBusy(true);
    setErrorMsg(null);
    try {
      const run = await runTestSimulation({
        agent_id: selectedAgentId,
        persona_id: selectedPersonaId,
        scenario_id: selectedScenarioId || null,
        voice_enabled: voiceEnabled,
        max_turns: maxTurns,
      });
      setActiveRun(run);
      await loadAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Simulation failed.");
    } finally {
      setBusy(false);
    }
  };

  const tabs: { id: LabTab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "simulator", label: "AI Client Simulator" },
    { id: "scenarios", label: "Scenario Builder" },
    { id: "live", label: "Live Test" },
    { id: "suites", label: "KB / Telephony / Perf / Recovery" },
    { id: "reports", label: "Test History & Reports" },
    { id: "assistant", label: "AI Testing Assistant" },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Testing Lab</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            End-to-end AI customer simulator, voice-to-voice pipeline verification, KB accuracy,
            compliance, and performance testing.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadAll()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
          <button
            type="button"
            disabled={busy || !selectedAgentId}
            onClick={() => {
              setTab("simulator");
              void handleRunSimulation();
            }}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" />
            Run Full Test
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-700 dark:text-rose-300">
          {errorMsg}
        </div>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-border pb-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === t.id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* OVERVIEW */}
      {tab === "overview" && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="text-xs text-muted-foreground">Total / Passed / Failed</div>
              <div className="mt-1 text-xl font-semibold">
                {stats?.total_runs ?? 0} /{" "}
                <span className="text-emerald-600">{stats?.passed_runs ?? 0}</span> /{" "}
                <span className="text-rose-600">{stats?.failed_runs ?? 0}</span>
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                Requires Review: {stats?.requires_review_runs ?? 0}
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="text-xs text-muted-foreground">Avg AI / STT / TTS Latency</div>
              <div className="mt-1 text-base font-mono font-semibold">
                {stats?.avg_ai_response_ms != null ? `${stats.avg_ai_response_ms}ms` : "—"} /{" "}
                {stats?.avg_stt_ms != null ? `${stats.avg_stt_ms}ms` : "—"} /{" "}
                {stats?.avg_tts_ms != null ? `${stats.avg_tts_ms}ms` : "—"}
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="text-xs text-muted-foreground">Completion & Quality Score</div>
              <div className="mt-1 text-xl font-semibold">
                {stats?.completion_rate_percent ?? 0}% ·{" "}
                {stats?.avg_quality_score != null ? `${stats.avg_quality_score}/100` : "—"}
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="text-xs text-muted-foreground">Telephony & Voice Errors</div>
              <div className="mt-1 text-sm font-medium">{stats?.telephony_status ?? "—"}</div>
              <div className="mt-1 text-xs text-muted-foreground">
                Voice Errors: {stats?.voice_pipeline_errors ?? 0}
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-border bg-card p-4 space-y-2">
              <div className="font-medium text-sm">Execution Mode Separation</div>
              <p className="text-xs text-muted-foreground">
                Mocked, Local Simulation, Real Microphone, and Real Telephony runs are tracked
                separately.
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs pt-2">
                {Object.entries(stats?.by_execution_mode ?? {}).map(([mode, count]) => (
                  <div key={mode} className="rounded-lg bg-muted/40 p-2 flex justify-between">
                    <span className="font-mono">{mode}</span>
                    <span className="font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4 space-y-2">
              <div className="font-medium text-sm">Results by Category</div>
              <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                {Object.entries(stats?.by_category ?? {}).map(([cat, c]) => (
                  <div key={cat} className="rounded-lg bg-muted/40 p-2 flex justify-between">
                    <span>{cat}</span>
                    <span className="font-mono">
                      {c.passed}/{c.total}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI CLIENT SIMULATOR */}
      {tab === "simulator" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-card p-5 grid gap-4 sm:grid-cols-4 items-end">
            <label className="text-xs space-y-1">
              <span>Target AI Agent</span>
              <select
                value={selectedAgentId}
                onChange={(e) => setSelectedAgentId(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-2.5 py-2"
              >
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.type})
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs space-y-1">
              <span>Customer Persona ({personas.length})</span>
              <select
                value={selectedPersonaId}
                onChange={(e) => setSelectedPersonaId(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-2.5 py-2"
              >
                {personas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.language})
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs space-y-1">
              <span>Scenario (Optional)</span>
              <select
                value={selectedScenarioId}
                onChange={(e) => setSelectedScenarioId(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-2.5 py-2"
              >
                <option value="">Default Persona Flow</option>
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-xs">
                <input
                  type="checkbox"
                  checked={voiceEnabled}
                  onChange={(e) => setVoiceEnabled(e.target.checked)}
                />
                Voice-to-Voice (STT+TTS)
              </label>
              <button
                type="button"
                disabled={busy || !selectedAgentId}
                onClick={() => void handleRunSimulation()}
                className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground disabled:opacity-50"
              >
                {busy ? "Simulating..." : "Run Simulation"}
              </button>
            </div>
          </div>

          {activeRun && (
            <div className="rounded-xl border border-border bg-card p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <FlaskConical className="h-4 w-4 text-primary" />
                  <span className="font-semibold text-sm">{activeRun.id}</span>
                  <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs">
                    {activeRun.execution_mode}
                  </span>
                  <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-medium">
                    {activeRun.status}
                  </span>
                </div>
                {activeRun.evaluation && (
                  <div className="text-sm font-semibold">
                    Score: {activeRun.evaluation.overall_score}/100
                  </div>
                )}
              </div>

              {activeRun.evaluation?.critical_failures.length ? (
                <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300 space-y-1">
                  <div className="font-semibold flex items-center gap-1.5">
                    <ShieldAlert className="h-4 w-4" /> Critical Failures
                  </div>
                  {activeRun.evaluation.critical_failures.map((cf, i) => (
                    <div key={i}>• {cf}</div>
                  ))}
                </div>
              ) : null}

              <div className="space-y-3">
                {activeRun.turns.map((t) => (
                  <div key={t.turn_number} className="rounded-lg border border-border p-3 text-xs space-y-1.5">
                    <div className="flex justify-between text-muted-foreground">
                      <span>Turn {t.turn_number}</span>
                      <span className="font-mono">
                        LLM: {t.llm_total_ms ?? "—"}ms · E2E: {t.end_to_end_ms ?? "—"}ms
                      </span>
                    </div>
                    <div>
                      <strong>Customer:</strong> {t.customer_text}
                    </div>
                    <div>
                      <strong>Agent:</strong> {t.agent_text || "—"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SCENARIO BUILDER */}
      {tab === "scenarios" && (
        <div className="space-y-6">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (!scenName || !scenObjective) return;
              await createTestingScenario({
                name: scenName,
                persona_id: scenPersona,
                objective: scenObjective,
                agent_id: selectedAgentId || null,
              });
              setScenName("");
              setScenObjective("");
              await loadAll();
            }}
            className="rounded-xl border border-border bg-card p-4 grid gap-3 sm:grid-cols-4 items-end"
          >
            <label className="text-xs space-y-1">
              <span>Scenario Name</span>
              <input
                value={scenName}
                onChange={(e) => setScenName(e.target.value)}
                placeholder="Enterprise Pricing Objection"
                className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
              />
            </label>
            <label className="text-xs space-y-1">
              <span>Persona</span>
              <select
                value={scenPersona}
                onChange={(e) => setScenPersona(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
              >
                {personas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs space-y-1">
              <span>Objective</span>
              <input
                value={scenObjective}
                onChange={(e) => setScenObjective(e.target.value)}
                placeholder="Validate pricing & no discount invention"
                className="w-full rounded-md border border-border bg-background px-2.5 py-1.5"
              />
            </label>
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground"
            >
              Save Scenario
            </button>
          </form>

          <div className="space-y-2">
            {scenarios.map((s) => (
              <div
                key={s.id}
                className="rounded-xl border border-border bg-card p-4 flex items-center justify-between"
              >
                <div>
                  <div className="font-medium text-sm">{s.name}</div>
                  <div className="text-xs text-muted-foreground">
                    Persona: {s.persona_id} · Language: {s.language} · Max Turns: {s.max_turns} —{" "}
                    {s.objective}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => void deleteTestingScenario(s.id).then(loadAll)}
                  className="rounded-md border border-rose-500/30 p-1.5 text-rose-600"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* LIVE TEST */}
      {tab === "live" && (
        <div className="rounded-xl border border-border bg-card p-6 space-y-4">
          <div className="flex items-center gap-2 font-medium">
            <Mic className="h-4 w-4 text-primary" />
            <span>Live Microphone Customer Conversation Test</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Test any agent directly using your real microphone and speakers over the production
            VoiceConversationService WebSocket pipeline — no telephony provider required. Every
            session is automatically monitored in Live Calls.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/playground"
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
            >
              <Mic className="h-3.5 w-3.5" />
              Launch Live Microphone Test
            </Link>
            <Link
              href="/live-calls"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-xs font-medium hover:bg-muted"
            >
              <Activity className="h-3.5 w-3.5" />
              Open Live Calls Monitor
            </Link>
          </div>
        </div>
      )}

      {/* SPECIALIZED SUITES */}
      {tab === "suites" && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!selectedAgentId || busy}
              onClick={async () => {
                setBusy(true);
                setSuiteOutput(await runKbSuiteTest({ agent_id: selectedAgentId }));
                setBusy(false);
              }}
              className="rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
            >
              Run Knowledge Base & Injection Test
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setSuiteOutput(
                  await runTelephonySuiteTest({
                    provider_id: "dry_run",
                    mode: "dry_run",
                    agent_id: selectedAgentId,
                  }),
                );
                setBusy(false);
              }}
              className="rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
            >
              Run Telephony Dry-Run Test
            </button>
            <button
              type="button"
              disabled={!selectedAgentId || busy}
              onClick={async () => {
                setBusy(true);
                setSuiteOutput(
                  await runPerformanceSuiteTest({
                    agent_id: selectedAgentId,
                    concurrency: 2,
                    iterations: 4,
                  }),
                );
                setBusy(false);
              }}
              className="rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
            >
              Run Local Concurrency Benchmark
            </button>
            <button
              type="button"
              disabled={!selectedAgentId || busy}
              onClick={async () => {
                setBusy(true);
                setSuiteOutput(await runFailureRecoverySuiteTest({ agent_id: selectedAgentId }));
                setBusy(false);
              }}
              className="rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
            >
              Run Failure & Recovery Checks
            </button>
          </div>
          {suiteOutput && (
            <pre className="rounded-xl border border-border bg-card p-4 text-xs overflow-x-auto">
              {JSON.stringify(suiteOutput, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* REPORTS */}
      {tab === "reports" && (
        <div className="space-y-3">
          {runs.length === 0 ? (
            <div className="rounded-xl border border-border bg-card p-6 text-xs text-muted-foreground">
              No test runs recorded yet.
            </div>
          ) : (
            runs.map((r) => (
              <div
                key={r.id}
                className="rounded-xl border border-border bg-card p-4 flex flex-wrap items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2 font-medium text-sm">
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                    <span>{r.scenario_name || r.persona_id}</span>
                    <span className="rounded bg-muted px-2 py-0.5 font-mono text-[11px]">
                      {r.execution_mode}
                    </span>
                    <span className="rounded border px-2 py-0.5 text-[11px]">{r.status}</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Agent: {r.agent_name} · Score: {r.evaluation?.overall_score ?? "—"}/100 ·{" "}
                    {new Date(r.started_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <a
                    href={getTestReportExportUrl(r.id, "json")}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs hover:bg-muted"
                  >
                    <Download className="h-3 w-3" /> JSON
                  </a>
                  <a
                    href={getTestReportExportUrl(r.id, "csv")}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs hover:bg-muted"
                  >
                    <Download className="h-3 w-3" /> CSV
                  </a>
                  <a
                    href={getTestReportExportUrl(r.id, "markdown")}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs hover:bg-muted"
                  >
                    <Download className="h-3 w-3" /> MD
                  </a>
                  {r.status === "FAILED" && (
                    <button
                      type="button"
                      onClick={() => void rerunFailedTest(r.id).then(loadAll)}
                      className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs hover:bg-muted"
                    >
                      <RotateCcw className="h-3 w-3" /> Rerun
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => void deleteTestRun(r.id).then(loadAll)}
                    className="rounded border border-rose-500/30 p-1 text-rose-600"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* AI TESTING ASSISTANT */}
      {tab === "assistant" && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-4">
          <div className="flex items-center gap-2 font-medium">
            <Sparkles className="h-4 w-4 text-primary" />
            <span>Autonomous AI Testing Assistant</span>
          </div>
          <textarea
            rows={3}
            value={assistantPrompt}
            onChange={(e) => setAssistantPrompt(e.target.value)}
            className="w-full rounded-lg border border-border bg-background p-3 text-xs"
          />
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!selectedAgentId || busy}
              onClick={async () => {
                setBusy(true);
                setAssistantResult(
                  await runTestingAssistant({
                    agent_id: selectedAgentId,
                    instruction: assistantPrompt,
                    execute: false,
                  }),
                );
                setBusy(false);
              }}
              className="rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-muted"
            >
              Inspect Readiness & Plan
            </button>
            <button
              type="button"
              disabled={!selectedAgentId || busy}
              onClick={async () => {
                setBusy(true);
                setAssistantResult(
                  await runTestingAssistant({
                    agent_id: selectedAgentId,
                    instruction: assistantPrompt,
                    execute: true,
                    voice_enabled: voiceEnabled,
                  }),
                );
                await loadAll();
                setBusy(false);
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground"
            >
              <Bot className="h-3.5 w-3.5" />
              Plan & Execute Authorized Tests
            </button>
          </div>
          {assistantResult && (
            <pre className="rounded-lg border border-border bg-muted/30 p-4 text-xs overflow-x-auto">
              {JSON.stringify(assistantResult, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
