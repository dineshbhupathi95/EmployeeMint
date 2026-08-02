import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquarePlus, Send, Sparkles, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface Conversation {
  id: string;
  title: string;
  updated_at: string | null;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { title: string; score: number }[];
  created_at: string | null;
}

const SUGGESTIONS = [
  "How many holidays are configured in our organization?",
  "What is my remaining leave balance?",
  "What leave types do we have and their quotas?",
  "What are the upcoming holidays?",
];

export function AssistantPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const [pendingAssistant, setPendingAssistant] = useState(false);
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: conversations } = useQuery({
    queryKey: ["assistant-conversations"],
    queryFn: () => apiRequest<Conversation[]>("/api/v1/assistant/conversations", { token: accessToken }),
  });

  const { data: thread, isFetching: threadLoading } = useQuery({
    queryKey: ["assistant-conversation", activeId],
    queryFn: () =>
      apiRequest<{ id: string; title: string; messages: ChatMessage[] }>(
        `/api/v1/assistant/conversations/${activeId}`,
        { token: accessToken },
      ),
    enabled: Boolean(activeId),
  });

  useEffect(() => {
    if (thread?.messages) {
      setLocalMessages(thread.messages);
      setPendingUser(null);
      setPendingAssistant(false);
    }
  }, [thread]);

  useEffect(() => {
    if (!activeId) {
      setLocalMessages([]);
      setPendingUser(null);
      setPendingAssistant(false);
    }
  }, [activeId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [localMessages, pendingAssistant, pendingUser]);

  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      apiRequest<{
        conversation_id: string;
        user_message: ChatMessage;
        message: ChatMessage;
      }>("/api/v1/assistant/chat", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ message, conversation_id: activeId }),
      }),
    onSuccess: (data) => {
      setActiveId(data.conversation_id);
      setLocalMessages((prev) => {
        const withoutPending = prev.filter((m) => !m.id.startsWith("temp-"));
        return [...withoutPending, data.user_message, data.message];
      });
      setPendingUser(null);
      setPendingAssistant(false);
      queryClient.invalidateQueries({ queryKey: ["assistant-conversations"] });
      queryClient.invalidateQueries({ queryKey: ["assistant-conversation", data.conversation_id] });
    },
    onError: (err: Error) => {
      setPendingAssistant(false);
      setLocalMessages((prev) => [
        ...prev.filter((m) => m.id !== "temp-assistant"),
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: err.message || "Something went wrong. Check Settings → AI Assistant.",
          sources: [],
          created_at: null,
        },
      ]);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`/api/v1/assistant/conversations/${id}`, {
        method: "DELETE",
        token: accessToken,
      }),
    onSuccess: (_, id) => {
      if (activeId === id) setActiveId(null);
      queryClient.invalidateQueries({ queryKey: ["assistant-conversations"] });
    },
  });

  function send(message: string) {
    const text = message.trim();
    if (!text || chatMutation.isPending) return;
    setInput("");
    setPendingUser(text);
    setPendingAssistant(true);
    setLocalMessages((prev) => [
      ...prev,
      {
        id: `temp-user-${Date.now()}`,
        role: "user",
        content: text,
        sources: [],
        created_at: null,
      },
    ]);
    chatMutation.mutate(text);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    send(input);
  }

  const showEmpty = !activeId && localMessages.length === 0 && !pendingAssistant;

  return (
    <div className="-m-4 flex h-[calc(100dvh-8.5rem)] min-h-[28rem] overflow-hidden border border-slate-200 bg-white sm:-m-6 lg:-m-8 lg:rounded-xl">
      {/* History */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-50 md:flex">
        <div className="border-b border-slate-200 p-3">
          <Button
            type="button"
            className="w-full"
            onClick={() => setActiveId(null)}
          >
            <MessageSquarePlus className="mr-2 h-4 w-4" />
            New chat
          </Button>
        </div>
        <div className="min-h-0 flex-1 space-y-0.5 overflow-y-auto p-2">
          {conversations?.length ? (
            conversations.map((c) => (
              <div
                key={c.id}
                className={cn(
                  "group flex items-center gap-1 rounded-lg",
                  activeId === c.id ? "bg-white shadow-sm ring-1 ring-slate-200" : "hover:bg-white/80",
                )}
              >
                <button
                  type="button"
                  onClick={() => setActiveId(c.id)}
                  className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm text-slate-700"
                >
                  {c.title}
                </button>
                <button
                  type="button"
                  title="Delete"
                  onClick={() => deleteMutation.mutate(c.id)}
                  className="mr-1 rounded p-1.5 text-slate-400 opacity-0 hover:bg-slate-100 hover:text-red-600 group-hover:opacity-100"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))
          ) : (
            <p className="px-3 py-6 text-center text-xs text-slate-400">No chats yet</p>
          )}
        </div>
      </aside>

      {/* Main chat */}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-slate-900">Company Assistant</h1>
            <p className="truncate text-xs text-slate-500">Ask about holidays, leave, and policies</p>
          </div>
          <Button
            type="button"
            variant="secondary"
            className="ml-auto md:hidden"
            onClick={() => setActiveId(null)}
          >
            New
          </Button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          {showEmpty && (
            <div className="mx-auto flex max-w-2xl flex-col items-center pt-10 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
                <Sparkles className="h-7 w-7" />
              </div>
              <h2 className="text-xl font-semibold text-slate-900">How can I help?</h2>
              <p className="mt-2 max-w-md text-sm text-slate-500">
                Answers use your live HR data and indexed company policies. Admins configure the model in Settings.
              </p>
              <div className="mt-8 grid w-full gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => send(s)}
                    className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm text-slate-700 transition hover:border-brand-200 hover:bg-brand-50/50"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {!showEmpty && (
            <div className="mx-auto max-w-2xl space-y-6">
              {threadLoading && activeId && localMessages.length === 0 && (
                <p className="text-sm text-slate-400">Loading conversation…</p>
              )}
              {localMessages.map((m) => (
                <div
                  key={m.id}
                  className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
                >
                  <div
                    className={cn(
                      "max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap",
                      m.role === "user"
                        ? "bg-brand-600 text-white"
                        : "bg-slate-100 text-slate-800",
                    )}
                  >
                    {m.content}
                    {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                      <div className="mt-3 border-t border-slate-200/80 pt-2 text-[11px] text-slate-500">
                        Sources: {m.sources.map((s) => s.title).join(", ")}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {pendingAssistant && (
                <div className="flex justify-start">
                  <div className="rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-500">
                    Thinking…
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <form onSubmit={onSubmit} className="border-t border-slate-200 p-4 sm:px-8">
          <div className="mx-auto flex max-w-2xl items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm focus-within:border-brand-300 focus-within:ring-2 focus-within:ring-brand-100">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              rows={1}
              placeholder="Ask about holidays, leave, policies…"
              className="max-h-32 min-h-[2.5rem] flex-1 resize-none bg-transparent px-2 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400"
            />
            <Button type="submit" disabled={!input.trim() || chatMutation.isPending} className="shrink-0">
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="mx-auto mt-2 max-w-2xl text-center text-[11px] text-slate-400">
            Answers are based on company data. Always verify critical HR decisions.
          </p>
        </form>
      </div>
    </div>
  );
}
