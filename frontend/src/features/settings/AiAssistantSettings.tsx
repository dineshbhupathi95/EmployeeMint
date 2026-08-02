import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useAuthStore } from "@/store/auth";

interface AiConfig {
  provider: string;
  base_url: string;
  model_name: string;
  embedding_model: string;
  is_enabled: boolean;
  has_api_key: boolean;
  api_key_masked: string | null;
}

interface AiDoc {
  id: string;
  title: string;
  source_type: string;
  status: string;
  chunk_count: number;
}

const PROVIDERS = [
  {
    id: "groq",
    label: "Groq",
    base_url: "https://api.groq.com/openai/v1",
    model_name: "llama-3.3-70b-versatile",
    embedding_model: "local",
    models: [
      "llama-3.3-70b-versatile",
      "llama-3.1-8b-instant",
      "llama-3.1-70b-versatile",
      "mixtral-8x7b-32768",
      "gemma2-9b-it",
    ],
    note: "Groq has no embeddings API — RAG uses local keyword search.",
  },
  {
    id: "openai",
    label: "OpenAI",
    base_url: "https://api.openai.com/v1",
    model_name: "gpt-4o-mini",
    embedding_model: "text-embedding-3-small",
    models: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "o4-mini"],
    note: null,
  },
  {
    id: "openai_compatible",
    label: "OpenAI-compatible (custom)",
    base_url: "https://api.openai.com/v1",
    model_name: "gpt-4o-mini",
    embedding_model: "text-embedding-3-small",
    models: [],
    note: "Set any OpenAI-compatible base URL (Azure, Together, Fireworks, etc.).",
  },
  {
    id: "ollama",
    label: "Ollama (local)",
    base_url: "http://localhost:11434/v1",
    model_name: "llama3.2",
    embedding_model: "nomic-embed-text",
    models: ["llama3.2", "llama3.1", "mistral", "qwen2.5"],
    note: "Run Ollama locally. API key can be any non-empty value (e.g. ollama).",
  },
] as const;

type ProviderId = (typeof PROVIDERS)[number]["id"];

function preset(id: string) {
  return PROVIDERS.find((p) => p.id === id) ?? PROVIDERS[0];
}

export function AiAssistantSettings() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    provider: "groq" as string,
    base_url: "https://api.groq.com/openai/v1",
    model_name: "llama-3.3-70b-versatile",
    embedding_model: "local",
    api_key: "",
    is_enabled: false,
  });
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [docTitle, setDocTitle] = useState("");
  const [docContent, setDocContent] = useState("");
  const [docFile, setDocFile] = useState<File | null>(null);

  const { data: config } = useQuery({
    queryKey: ["assistant-config"],
    queryFn: () => apiRequest<AiConfig>("/api/v1/assistant/config", { token: accessToken }),
  });

  const { data: docs } = useQuery({
    queryKey: ["assistant-documents"],
    queryFn: () => apiRequest<AiDoc[]>("/api/v1/assistant/documents", { token: accessToken }),
  });

  useEffect(() => {
    if (!config) return;
    setForm({
      provider: config.provider || "groq",
      base_url: config.base_url,
      model_name: config.model_name,
      embedding_model: config.embedding_model,
      api_key: "",
      is_enabled: config.is_enabled,
    });
  }, [config]);

  const selected = preset(form.provider);

  function applyProvider(id: ProviderId) {
    const p = preset(id);
    setForm((f) => ({
      ...f,
      provider: p.id,
      base_url: p.base_url,
      model_name: p.model_name,
      embedding_model: p.embedding_model,
    }));
  }

  const save = useMutation({
    mutationFn: () =>
      apiRequest<AiConfig>("/api/v1/assistant/config", {
        method: "PUT",
        token: accessToken,
        body: JSON.stringify({
          provider: form.provider,
          base_url: form.base_url,
          model_name: form.model_name,
          embedding_model: form.embedding_model,
          // Saving always turns the assistant on (toggle can still disable on next save)
          is_enabled: true,
          ...(form.api_key.trim() ? { api_key: form.api_key.trim() } : {}),
        }),
      }),
    onSuccess: () => {
      setMsg("Saved — Company Assistant is now enabled");
      setErr("");
      setForm((f) => ({ ...f, api_key: "", is_enabled: true }));
      queryClient.invalidateQueries({ queryKey: ["assistant-config"] });
    },
    onError: (e: Error) => {
      setErr(e.message);
      setMsg("");
    },
  });

  const test = useMutation({
    mutationFn: () =>
      apiRequest<{ ok: boolean; reply: string }>("/api/v1/assistant/config/test", {
        method: "POST",
        token: accessToken,
      }),
    onSuccess: (r) => {
      setMsg(`Connection OK — model replied: ${r.reply}`);
      setErr("");
    },
    onError: (e: Error) => {
      setErr(e.message);
      setMsg("");
    },
  });

  const sync = useMutation({
    mutationFn: () =>
      apiRequest<{ synced: number }>("/api/v1/assistant/sync", {
        method: "POST",
        token: accessToken,
      }),
    onSuccess: (r) => {
      setMsg(`Synced ${r.synced} knowledge sources into the vector index`);
      setErr("");
      queryClient.invalidateQueries({ queryKey: ["assistant-documents"] });
    },
    onError: (e: Error) => {
      setErr(e.message);
      setMsg("");
    },
  });

  const addDoc = useMutation({
    mutationFn: async () => {
      if (docFile) {
        const body = new FormData();
        body.append("file", docFile);
        if (docTitle.trim()) body.append("title", docTitle.trim());
        return apiRequest("/api/v1/assistant/documents/upload", {
          method: "POST",
          token: accessToken,
          body,
        });
      }
      return apiRequest("/api/v1/assistant/documents", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ title: docTitle, content: docContent }),
      });
    },
    onSuccess: () => {
      const wasUpload = Boolean(docFile);
      setDocTitle("");
      setDocContent("");
      setDocFile(null);
      setMsg(wasUpload ? "Policy file uploaded and indexed" : "Policy document indexed");
      setErr("");
      queryClient.invalidateQueries({ queryKey: ["assistant-documents"] });
    },
    onError: (e: Error) => setErr(e.message),
  });

  const removeDoc = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`/api/v1/assistant/documents/${id}`, { method: "DELETE", token: accessToken }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assistant-documents"] }),
  });

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Model configuration"
          description="Choose a provider, paste your API key, and pick a model. Settings are stored per organization."
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <label className="block text-sm font-medium text-slate-700" htmlFor="ai-provider">
              Provider
            </label>
            <select
              id="ai-provider"
              value={form.provider}
              onChange={(e) => applyProvider(e.target.value as ProviderId)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-opacity-20"
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
            {selected.note && <p className="text-xs text-slate-500">{selected.note}</p>}
          </div>

          <Input
            label="Base URL"
            value={form.base_url}
            onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))}
            placeholder="https://api.groq.com/openai/v1"
          />

          <Input
            label="Chat model name"
            value={form.model_name}
            onChange={(e) => setForm((f) => ({ ...f, model_name: e.target.value }))}
            placeholder={
              form.provider === "groq"
                ? "llama-3.3-70b-versatile"
                : form.provider === "ollama"
                  ? "llama3.2"
                  : "gpt-4o-mini"
            }
          />
          {selected.models.length > 0 && (
            <p className="text-xs text-slate-500 sm:col-span-2 -mt-2">
              Examples for {selected.label}: {selected.models.join(", ")}
            </p>
          )}

          <Input
            label="Embedding model"
            value={form.embedding_model}
            onChange={(e) => setForm((f) => ({ ...f, embedding_model: e.target.value }))}
            placeholder="local"
          />
          <p className="text-xs text-slate-500 sm:col-span-2 -mt-2">
            Use <code className="rounded bg-slate-100 px-1">local</code> for Groq (keyword RAG). Use{" "}
            <code className="rounded bg-slate-100 px-1">text-embedding-3-small</code> with OpenAI.
          </p>

          <div className="sm:col-span-2">
            <Input
              label="API key"
              type="password"
              value={form.api_key}
              onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
              placeholder={
                config?.has_api_key
                  ? `Configured (${config.api_key_masked}) — enter new key to replace`
                  : form.provider === "groq"
                    ? "gsk_..."
                    : "sk-..."
              }
              autoComplete="off"
            />
          </div>
          <label className="flex items-start gap-3 rounded-lg border border-brand-200 bg-brand-50/60 px-4 py-3 text-sm text-slate-800 sm:col-span-2">
            <input
              type="checkbox"
              checked={form.is_enabled}
              onChange={(e) => setForm((f) => ({ ...f, is_enabled: e.target.checked }))}
              className="mt-0.5 rounded border-slate-300"
            />
            <span>
              <span className="font-semibold text-brand-800">Enable Company Assistant</span>
              <span className="mt-0.5 block text-xs text-slate-600">
                Required for chat. Leave this checked, then click Save.
              </span>
            </span>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="button" onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save"}
          </Button>
          <Button type="button" variant="secondary" onClick={() => test.mutate()} disabled={test.isPending}>
            {test.isPending ? "Testing…" : "Test connection"}
          </Button>
          <Button type="button" variant="secondary" onClick={() => sync.mutate()} disabled={sync.isPending}>
            {sync.isPending ? "Syncing…" : "Sync company data"}
          </Button>
        </div>
        {msg && <p className="mt-3 text-sm text-emerald-700">{msg}</p>}
        {err && <p className="mt-3 text-sm text-red-600">{err}</p>}
      </Card>

      <Card>
        <CardHeader
          title="Policy documents"
          description="Upload a file or paste text. Files are extracted, chunked, and indexed for RAG."
        />
        <div className="space-y-3">
          <Input
            label="Title (optional for uploads — defaults to filename)"
            value={docTitle}
            onChange={(e) => setDocTitle(e.target.value)}
            placeholder="Leave policy"
          />
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700">Upload file</label>
            <input
              type="file"
              accept=".txt,.md,.markdown,.csv,.pdf,.docx,text/plain,application/pdf"
              onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
            />
            <p className="text-xs text-slate-500">
              Supported: .txt, .md, .csv, .pdf (max 8 MB). Content text is not required when a file is selected.
              {docFile ? ` Selected: ${docFile.name}` : ""}
            </p>
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700">
              Or paste content {docFile ? "(optional if file selected)" : ""}
            </label>
            <textarea
              value={docContent}
              onChange={(e) => setDocContent(e.target.value)}
              rows={5}
              disabled={Boolean(docFile)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-opacity-20 disabled:bg-slate-50 disabled:text-slate-400"
              placeholder={docFile ? "Using uploaded file — paste not needed" : "Paste policy text…"}
            />
          </div>
          <Button
            type="button"
            onClick={() => {
              setErr("");
              addDoc.mutate();
            }}
            disabled={
              addDoc.isPending ||
              (!docFile && (!docTitle.trim() || !docContent.trim()))
            }
          >
            {addDoc.isPending ? "Indexing…" : docFile ? "Upload & index" : "Add & index"}
          </Button>
        </div>

        <div className="mt-6 overflow-x-auto">
          <table className="em-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Source</th>
                <th>Status</th>
                <th>Chunks</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {docs?.map((d) => (
                <tr key={d.id}>
                  <td>{d.title}</td>
                  <td>{d.source_type}</td>
                  <td>{d.status}</td>
                  <td>{d.chunk_count}</td>
                  <td>
                    {(d.source_type === "manual" || d.source_type === "upload") && (
                      <button
                        type="button"
                        className="text-sm text-red-600 hover:underline"
                        onClick={() => removeDoc.mutate(d.id)}
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {!docs?.length && (
                <tr>
                  <td colSpan={5} className="text-slate-400">
                    No documents yet — sync company data, paste text, or upload a file.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
