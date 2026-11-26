"use client";

import type { ChatMessage } from "@agentvoice/shared-types";
import {
  ArrowLeft,
  Bot,
  MessageSquarePlus,
  Send,
  Square,
  Trash2,
  User,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAgent } from "@/hooks/use-agents";
import {
  useAgentConversations,
  useConversation,
  useCreateConversation,
  useDeleteConversation,
} from "@/hooks/use-conversations";
import { streamConversationMessage } from "@/lib/api-client";

export default function AgentPlaygroundPage() {
  const params = useParams<{ id: string }>();
  const agentId = params.id;

  const agentQuery = useAgent(agentId);
  const convListQuery = useAgentConversations(agentId);
  const createConvMutation = useCreateConversation(agentId);
  const deleteConvMutation = useDeleteConversation(agentId);

  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const convQuery = useConversation(selectedConvId);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingText, setStreamingText] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [input, setInput] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

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

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            href={`/agents/${agentId}`}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card hover:bg-muted"
            aria-label="Back to agent"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              AI Chat Playground {agent ? `· ${agent.name}` : ""}
            </h1>
            <p className="text-xs text-muted-foreground">
              Text-based local LLM testing (Phase 3). Voice microphone input arrives in Phase 4.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => void handleNewConversation()}
          disabled={createConvMutation.isPending}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          <MessageSquarePlus className="h-4 w-4" />
          New Conversation
        </button>
      </div>

      {errorMessage && (
        <div
          role="alert"
          className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-sm text-rose-700 dark:text-rose-300"
        >
          {errorMessage}{" "}
          {errorMessage.toLowerCase().includes("model manager") && (
            <Link href="/models" className="underline font-medium">
              Open Model Manager
            </Link>
          )}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-4">
        {/* Conversation List */}
        <aside className="rounded-xl border border-border bg-card p-3 space-y-2 lg:col-span-1">
          <div className="px-2 py-1 text-xs font-semibold text-muted-foreground">
            Saved Conversations
          </div>
          {conversations.length === 0 ? (
            <p className="px-2 py-3 text-xs text-muted-foreground">
              No conversations yet. Send a message to start.
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

        {/* Chat Area */}
        <div className="flex h-[560px] flex-col rounded-xl border border-border bg-card lg:col-span-3">
          <div className="flex items-center justify-between border-b border-border px-4 py-2.5 text-xs text-muted-foreground">
            <span>
              Model:{" "}
              <code className="font-mono text-foreground">
                {convQuery.data?.model_id ?? agent?.model?.model_id ?? "Default local model"}
              </code>
            </span>
            {isStreaming && <span className="text-primary font-medium">Generating...</span>}
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.length === 0 && !streamingText && (
              <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
                Send a message in Hindi, Hinglish, or English to test your local LLM agent.
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
                  {msg.role === "assistant" && msg.duration_ms != null && (
                    <div className="mt-1.5 text-[10px] text-muted-foreground">
                      {msg.model_id} · {(msg.duration_ms / 1000).toFixed(2)}s
                    </div>
                  )}
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
        </div>
      </div>
    </div>
  );
}
