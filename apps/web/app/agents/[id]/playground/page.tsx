"use client";

import type { ChatMessage } from "@agentvoice/shared-types";
import { STATUS_TONE_CLASSES } from "@agentvoice/ui";
import {
  ArrowLeft,
  Bot,
  Hand,
  MessageSquare,
  MessageSquarePlus,
  Mic,
  MicOff,
  PhoneOff,
  Send,
  Square,
  Trash2,
  User,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { AgentAvatar } from "@/components/agents/agent-badges";
import { useAgent } from "@/hooks/use-agents";
import {
  useAgentConversations,
  useConversation,
  useCreateConversation,
  useDeleteConversation,
} from "@/hooks/use-conversations";
import { useSpeechHealth } from "@/hooks/use-speech";
import { useVoiceSession } from "@/hooks/use-voice-session";
import { streamConversationMessage } from "@/lib/api-client";

export default function AgentPlaygroundPage() {
  const params = useParams<{ id: string }>();
  const agentId = params.id;

  const agentQuery = useAgent(agentId);
  const speechHealthQuery = useSpeechHealth();
  const convListQuery = useAgentConversations(agentId);
  const createConvMutation = useCreateConversation(agentId);
  const deleteConvMutation = useDeleteConversation(agentId);

  const [mode, setMode] = useState<"voice" | "text">("voice");
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const convQuery = useConversation(selectedConvId);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingText, setStreamingText] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [input, setInput] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const handleVoiceTranscript = useCallback((text: string) => {
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text, timestamp: new Date().toISOString() },
    ]);
  }, []);

  const handleVoiceReply = useCallback((text: string) => {
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: text, timestamp: new Date().toISOString() },
    ]);
  }, []);

  const voice = useVoiceSession({
    agentId,
    conversationId: selectedConvId,
    onTranscriptFinal: handleVoiceTranscript,
    onResponseText: handleVoiceReply,
  });

  useEffect(() => {
    if (voice.session?.conversation_id && !selectedConvId) {
      setSelectedConvId(voice.session.conversation_id);
      void convListQuery.refetch();
    }
  }, [voice.session?.conversation_id, selectedConvId, convListQuery]);

  useEffect(() => {
    if (!selectedConvId && convListQuery.data && convListQuery.data.length > 0) {
      setSelectedConvId(convListQuery.data[0].id);
    }
  }, [convListQuery.data, selectedConvId]);

  useEffect(() => {
    if (convQuery.data) {
      setMessages(convQuery.data.messages);
    } else if (!selectedConvId) {
      setMessages([]);
    }
  }, [convQuery.data, selectedConvId]);

  const handleNewConversation = async () => {
    setErrorMessage(null);
    try {
      const conv = await createConvMutation.mutateAsync("New Conversation");
      setSelectedConvId(conv.id);
      setMessages([]);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to start conversation.");
    }
  };

  const handleDeleteConversation = async (convId: string) => {
    setErrorMessage(null);
    try {
      await deleteConvMutation.mutateAsync(convId);
      if (selectedConvId === convId) {
        setSelectedConvId(null);
        setMessages([]);
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to delete conversation.");
    }
  };

  const handleStopStreaming = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setStreamingText("");
  };

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    setErrorMessage(null);

    let activeConvId = selectedConvId;
    if (!activeConvId) {
      try {
        const created = await createConvMutation.mutateAsync(trimmed.slice(0, 48));
        activeConvId = created.id;
        setSelectedConvId(created.id);
      } catch (err) {
        setErrorMessage(err instanceof Error ? err.message : "Failed to create conversation.");
        return;
      }
    }

    const optimisticUserMsg: ChatMessage = {
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUserMsg]);
    setInput("");
    setIsStreaming(true);
    setStreamingText("");

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamConversationMessage(
        activeConvId,
        trimmed,
        (event) => {
          if (event.event === "delta") {
            setStreamingText((prev) => prev + event.content);
          } else if (event.event === "done") {
            setStreamingText("");
            setMessages((prev) => [...prev, event.message]);
            void convQuery.refetch();
          } else if (event.event === "error") {
            setErrorMessage(event.message);
            setStreamingText("");
          }
        },
        controller.signal,
      );
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setErrorMessage(err instanceof Error ? err.message : "Failed to stream response.");
      }
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
    }
  };

  const agent = agentQuery.data;
  const conversations = convListQuery.data ?? [];
  const speechHealth = speechHealthQuery.data;
  const combinedError = voice.error ?? errorMessage;

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            href={`/agents/${agentId}`}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
            aria-label="Back to agent"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <AgentAvatar avatar={agent?.avatar ?? "bot"} />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              Voice &amp; Chat Playground {agent ? `· ${agent.name}` : ""}
            </h1>
            <p className="text-xs text-muted-foreground">
              LLM: <code>{agent?.model?.model_id || "default"}</code> · STT:{" "}
              <code>{speechHealth?.stt.provider ?? "faster-whisper"}</code> · TTS:{" "}
              <code>{agent?.voice.provider ?? "piper"}</code> (
              <code>{agent?.voice.voice_id ?? "default"}</code>)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-lg border border-border bg-card p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setMode("voice")}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium ${
                mode === "voice" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
              }`}
            >
              <Mic className="h-3.5 w-3.5" />
              Voice
            </button>
            <button
              type="button"
              onClick={() => setMode("text")}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium ${
                mode === "text" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              Text
            </button>
          </div>

          <button
            type="button"
            onClick={() => void handleNewConversation()}
            disabled={createConvMutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted disabled:opacity-50"
          >
            <MessageSquarePlus className="h-4 w-4" />
            New
          </button>
        </div>
      </div>

      {/* Speech Provider Readiness Warning (honest runtime feedback) */}
      {mode === "voice" && speechHealth && (!speechHealth.stt.available || !speechHealth.tts.available) && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-800 dark:text-amber-200 space-y-1">
          <div className="font-semibold">Local Speech Runtime Notice</div>
          {!speechHealth.stt.available && <div>STT: {speechHealth.stt.error}</div>}
          {!speechHealth.tts.available && <div>TTS: {speechHealth.tts.error}</div>}
        </div>
      )}

      {combinedError && (
        <div
          role="alert"
          className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300"
        >
          {combinedError}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-4">
        {/* Saved Conversations */}
        <aside className="rounded-xl border border-border bg-card p-3 space-y-2 lg:col-span-1">
          <div className="px-2 py-1 text-xs font-semibold text-muted-foreground">
            Saved Conversations
          </div>
          {conversations.length === 0 ? (
            <p className="px-2 py-3 text-xs text-muted-foreground">
              No conversations yet.
            </p>
          ) : (
            <div className="space-y-1">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`flex items-center justify-between rounded-lg px-2.5 py-2 text-xs ${
                    selectedConvId === conv.id
                      ? "bg-primary/10 text-primary font-medium"
                      : "hover:bg-muted"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setSelectedConvId(conv.id)}
                    className="flex-1 truncate text-left"
                  >
                    {conv.title}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDeleteConversation(conv.id)}
                    aria-label="Delete conversation"
                    className="ml-2 text-muted-foreground hover:text-rose-500"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </aside>

        {/* Main Playground Area */}
        <div className="flex h-[580px] flex-col rounded-xl border border-border bg-card lg:col-span-3">
          {/* Status & Audio Bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-2.5 text-xs">
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-medium ${
                  STATUS_TONE_CLASSES[
                    voice.sessionState === "ERROR"
                      ? "unavailable"
                      : voice.isConnected
                        ? "healthy"
                        : "neutral"
                  ]
                }`}
              >
                {voice.sessionState}
              </span>
              {voice.latency && (
                <span className="text-muted-foreground">
                  STT {voice.latency.stt_ms}ms · LLM {voice.latency.llm_total_ms}ms · TTS{" "}
                  {voice.latency.tts_ms}ms · Total {voice.latency.total_ms}ms
                </span>
              )}
            </div>

            {mode === "voice" && (
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">Mic Level</span>
                  <div className="h-2 w-20 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full bg-primary transition-all duration-75"
                      style={{ width: `${Math.round(voice.audioLevel * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Transcript / Messages */}
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.length === 0 && !streamingText && (
              <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
                {mode === "voice"
                  ? 'Click "Start Conversation" and speak in Hindi, Hinglish, or English.'
                  : "Send a text message to test your local LLM agent."}
              </div>
            )}

            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Bot className="h-4 w-4" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "border border-border bg-muted/40"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
                {msg.role === "user" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted text-foreground">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}

            {streamingText && (
              <div className="flex gap-3 justify-start">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="max-w-[80%] rounded-xl border border-border bg-muted/40 px-4 py-2.5 text-sm">
                  <p className="whitespace-pre-wrap">{streamingText}</p>
                </div>
              </div>
            )}
          </div>

          {/* Controls */}
          {mode === "voice" ? (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border p-3">
              <div className="flex flex-wrap items-center gap-2">
                {!voice.isConnected ? (
                  <button
                    type="button"
                    onClick={() => void voice.startConversation()}
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
                  >
                    <Mic className="h-4 w-4" />
                    Start Conversation
                  </button>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={voice.endConversation}
                      className="inline-flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700"
                    >
                      <PhoneOff className="h-4 w-4" />
                      End Conversation
                    </button>
                    <button
                      type="button"
                      onClick={() => voice.setIsMuted(!voice.isMuted)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
                    >
                      {voice.isMuted ? (
                        <>
                          <MicOff className="h-4 w-4 text-rose-500" />
                          Unmute
                        </>
                      ) : (
                        <>
                          <Mic className="h-4 w-4" />
                          Mute
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={voice.interrupt}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
                    >
                      <Hand className="h-4 w-4" />
                      Interrupt
                    </button>
                  </>
                )}
              </div>

              {voice.microphones.length > 0 && (
                <select
                  value={voice.selectedMicId}
                  onChange={(e) => voice.setSelectedMicId(e.target.value)}
                  aria-label="Select microphone"
                  className="rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs"
                >
                  <option value="">Default Microphone</option>
                  {voice.microphones.map((m) => (
                    <option key={m.deviceId} value={m.deviceId}>
                      {m.label}
                    </option>
                  ))}
                </select>
              )}
            </div>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void handleSend();
              }}
              className="flex items-center gap-2 border-t border-border p-3"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type a message in Hindi, Hinglish, or English..."
                disabled={isStreaming}
                className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none disabled:opacity-50"
              />
              {isStreaming ? (
                <button
                  type="button"
                  onClick={handleStopStreaming}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700"
                >
                  <Square className="h-3.5 w-3.5" />
                  Stop
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
                >
                  <Send className="h-4 w-4" />
                  Send
                </button>
              )}
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
