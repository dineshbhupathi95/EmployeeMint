import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Eye, FileUp, Plus, Send, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { apiDownload, apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface OfferTemplate {
  id: string;
  name: string;
  body_html: string;
  is_active: boolean;
}

interface OfferLetter {
  id: string;
  candidate_name: string;
  candidate_email: string;
  designation: string | null;
  ctc: string | null;
  joining_date: string | null;
  status: string;
  has_pdf: boolean;
  template_id: string | null;
  template_name: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700",
  pdf_ready: "bg-brand-100 text-brand-800",
  released: "bg-green-100 text-green-800",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  pdf_ready: "PDF Ready",
  released: "Released",
};

const PLACEHOLDERS = [
  "candidate_name",
  "candidate_email",
  "designation",
  "ctc",
  "joining_date",
  "company_name",
  "date",
];

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export function OfferLettersPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"offers" | "templates">("offers");
  const [form, setForm] = useState({
    template_id: "",
    candidate_name: "",
    candidate_email: "",
    designation: "",
    ctc: "",
    joining_date: "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<OfferTemplate | null>(null);
  const [templateForm, setTemplateForm] = useState({ name: "", body_html: "", is_active: true });
  const [uploadName, setUploadName] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const { data: templates } = useQuery({
    queryKey: ["offer-templates"],
    queryFn: () => apiRequest<OfferTemplate[]>("/api/v1/offer-letter-templates", { token: accessToken }),
  });

  const { data: letters } = useQuery({
    queryKey: ["offer-letters"],
    queryFn: () => apiRequest<OfferLetter[]>("/api/v1/offer-letters", { token: accessToken }),
  });

  const activeTemplates = templates?.filter((t) => t.is_active) ?? [];

  useEffect(() => {
    if (!form.template_id && activeTemplates.length === 1) {
      setForm((f) => ({ ...f, template_id: activeTemplates[0].id }));
    }
  }, [activeTemplates, form.template_id]);

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest("/api/v1/offer-letters", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          ...form,
          template_id: form.template_id,
          joining_date: form.joining_date || null,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offer-letters"] });
      setForm((f) => ({
        ...f,
        candidate_name: "",
        candidate_email: "",
        designation: "",
        ctc: "",
        joining_date: "",
      }));
      setMessage("Offer draft created from selected template. Generate PDF next.");
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const saveTemplateMutation = useMutation({
    mutationFn: () => {
      if (editingTemplate) {
        return apiRequest(`/api/v1/offer-letter-templates/${editingTemplate.id}`, {
          method: "PATCH",
          token: accessToken,
          body: JSON.stringify(templateForm),
        });
      }
      return apiRequest("/api/v1/offer-letter-templates", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify(templateForm),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offer-templates"] });
      setShowTemplateModal(false);
      setEditingTemplate(null);
      setMessage(editingTemplate ? "Template updated." : "Template created.");
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const deleteTemplateMutation = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`/api/v1/offer-letter-templates/${id}`, { method: "DELETE", token: accessToken }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offer-templates"] });
      setMessage("Template deleted.");
    },
    onError: (err: Error) => setError(err.message),
  });

  const uploadTemplate = async () => {
    if (!uploadFile || !uploadName.trim()) {
      setError("Template name and file are required");
      return;
    }
    const body = new FormData();
    body.append("name", uploadName.trim());
    body.append("file", uploadFile);
    body.append("is_active", "true");
    try {
      const res = await fetch(`${API_BASE}/api/v1/offer-letter-templates/upload`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.error?.message || res.statusText);
      }
      queryClient.invalidateQueries({ queryKey: ["offer-templates"] });
      setUploadFile(null);
      setUploadName("");
      setMessage("Template uploaded successfully.");
      setError("");
      setTab("templates");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const loadSampleBody = async () => {
    const sample = await apiRequest<{ body_html: string }>("/api/v1/offer-letter-templates/sample-body", {
      token: accessToken,
    });
    setTemplateForm((f) => ({ ...f, body_html: sample.body_html }));
  };

  const openCreateTemplate = async () => {
    setEditingTemplate(null);
    setTemplateForm({ name: "", body_html: "", is_active: true });
    setShowTemplateModal(true);
    try {
      await loadSampleBody();
    } catch {
      /* ignore */
    }
  };

  const openEditTemplate = (t: OfferTemplate) => {
    setEditingTemplate(t);
    setTemplateForm({ name: t.name, body_html: t.body_html, is_active: t.is_active });
    setShowTemplateModal(true);
  };

  const generatePdf = async (id: string, name: string) => {
    try {
      const blob = await apiDownload(`/api/v1/offer-letters/${id}/generate-pdf`, accessToken, "POST");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `offer-${name.replace(/\s+/g, "-").toLowerCase()}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      queryClient.invalidateQueries({ queryKey: ["offer-letters"] });
      setMessage("PDF generated from template and downloaded.");
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate PDF");
    }
  };

  const viewPdf = async (id: string) => {
    try {
      const blob = await apiDownload(`/api/v1/offer-letters/${id}/pdf`, accessToken);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open PDF");
    }
  };

  const releaseMutation = useMutation({
    mutationFn: (id: string) =>
      apiRequest<{ message: string }>(`/api/v1/offer-letters/${id}/release`, {
        method: "POST",
        token: accessToken,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["offer-letters"] });
      setMessage(data.message);
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Offer Letters"
        description="Manage templates, create offers from a template, generate PDF, then release"
      />

      <div className="flex gap-2 border-b border-slate-200">
        {(["offers", "templates"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn(
              "border-b-2 px-4 py-2 text-sm font-medium capitalize",
              tab === t ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500",
            )}
          >
            {t === "offers" ? "Offers" : `Templates (${templates?.length ?? 0})`}
          </button>
        ))}
      </div>

      {message && <p className="rounded-lg bg-green-50 px-4 py-2 text-sm text-green-700">{message}</p>}
      {error && <p className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      {tab === "templates" && (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader title="Create template in app" description="Write body with placeholders" />
              <Button onClick={openCreateTemplate}>
                <Plus className="mr-2 h-4 w-4" /> New Template
              </Button>
              <p className="mt-3 text-xs text-slate-500">
                Placeholders: {PLACEHOLDERS.map((p) => `{{${p}}}`).join(", ")}
              </p>
            </Card>
            <Card>
              <CardHeader title="Upload template file" description="Upload .html, .txt, or .md" />
              <div className="space-y-3">
                <Input
                  label="Template Name"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                  placeholder="e.g. Standard Full-time Offer"
                />
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">File</label>
                  <input
                    type="file"
                    accept=".html,.htm,.txt,.md"
                    className="block w-full text-sm text-slate-600"
                    onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  />
                </div>
                <Button onClick={uploadTemplate} disabled={!uploadFile || !uploadName.trim()}>
                  <FileUp className="mr-2 h-4 w-4" /> Upload Template
                </Button>
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader title="Saved templates" description="Active templates can be selected when creating offers" />
            <div className="space-y-3">
              {templates?.map((t) => (
                <div key={t.id} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-900">{t.name}</p>
                      <p className="mt-1 text-xs text-slate-500 line-clamp-2">{t.body_html.slice(0, 160)}...</p>
                      <span
                        className={cn(
                          "mt-2 inline-block rounded-full px-2 py-0.5 text-xs font-medium",
                          t.is_active ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-600",
                        )}
                      >
                        {t.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="secondary" onClick={() => openEditTemplate(t)}>
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          if (confirm(`Delete template "${t.name}"?`)) deleteTemplateMutation.mutate(t.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              {!templates?.length && (
                <p className="py-6 text-center text-sm text-slate-500">
                  No templates yet. Create one in the app or upload a file first.
                </p>
              )}
            </div>
          </Card>
        </>
      )}

      {tab === "offers" && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <Card className="border-l-4 border-l-slate-300">
              <p className="text-xs font-medium uppercase text-slate-400">Step 1</p>
              <p className="mt-1 font-semibold text-slate-900">Select Template</p>
              <p className="mt-1 text-sm text-slate-500">Offer is created from that template only</p>
            </Card>
            <Card className="border-l-4 border-l-brand-400">
              <p className="text-xs font-medium uppercase text-brand-500">Step 2</p>
              <p className="mt-1 font-semibold text-slate-900">Generate PDF</p>
              <p className="mt-1 text-sm text-slate-500">Placeholders filled from candidate details</p>
            </Card>
            <Card className="border-l-4 border-l-green-400">
              <p className="text-xs font-medium uppercase text-green-600">Step 3</p>
              <p className="mt-1 font-semibold text-slate-900">Release Offer</p>
              <p className="mt-1 text-sm text-slate-500">Mark as sent to candidate</p>
            </Card>
          </div>

          <Card>
            <CardHeader title="New Offer Letter" description="Template is required — create one under Templates if the list is empty" />
            {!activeTemplates.length ? (
              <div className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
                No active templates.{" "}
                <button type="button" className="font-medium underline" onClick={() => setTab("templates")}>
                  Create or upload a template
                </button>{" "}
                before creating an offer.
              </div>
            ) : (
              <form
                className="grid gap-3 sm:grid-cols-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!form.template_id) {
                    setError("Please select a template");
                    return;
                  }
                  createMutation.mutate();
                }}
              >
                <div className="sm:col-span-2">
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">Template *</label>
                  <select
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                    required
                    value={form.template_id}
                    onChange={(e) => setForm((f) => ({ ...f, template_id: e.target.value }))}
                  >
                    <option value="">Select template...</option>
                    {activeTemplates.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>
                <Input
                  label="Candidate Name"
                  value={form.candidate_name}
                  onChange={(e) => setForm((f) => ({ ...f, candidate_name: e.target.value }))}
                  required
                />
                <Input
                  label="Email"
                  type="email"
                  value={form.candidate_email}
                  onChange={(e) => setForm((f) => ({ ...f, candidate_email: e.target.value }))}
                  required
                />
                <Input
                  label="Designation"
                  value={form.designation}
                  onChange={(e) => setForm((f) => ({ ...f, designation: e.target.value }))}
                />
                <Input
                  label="CTC"
                  value={form.ctc}
                  onChange={(e) => setForm((f) => ({ ...f, ctc: e.target.value }))}
                  placeholder="e.g. 12 LPA"
                />
                <Input
                  label="Joining Date"
                  type="date"
                  value={form.joining_date}
                  onChange={(e) => setForm((f) => ({ ...f, joining_date: e.target.value }))}
                />
                <div className="flex items-end sm:col-span-2">
                  <Button type="submit" disabled={createMutation.isPending}>
                    {createMutation.isPending ? "Creating..." : "Create Draft from Template"}
                  </Button>
                </div>
              </form>
            )}
          </Card>

          <Card>
            <CardHeader title="All Offer Letters" />
            <div className="overflow-x-auto">
              <table className="w-full min-w-max text-left text-sm">
                <thead>
                  <tr className="border-b text-slate-500">
                    <th className="pb-2 pr-4">Candidate</th>
                    <th className="pb-2 pr-4">Template</th>
                    <th className="pb-2 pr-4">Joining</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {letters?.map((l) => (
                    <tr key={l.id} className="border-b border-slate-100">
                      <td className="py-3 pr-4">
                        <p className="font-medium text-slate-900">{l.candidate_name}</p>
                        <p className="text-xs text-slate-500">{l.candidate_email}</p>
                      </td>
                      <td className="py-3 pr-4 text-slate-600">{l.template_name ?? "—"}</td>
                      <td className="py-3 pr-4 text-slate-600">{l.joining_date ?? "—"}</td>
                      <td className="py-3 pr-4">
                        <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", STATUS_STYLES[l.status] ?? STATUS_STYLES.draft)}>
                          {STATUS_LABELS[l.status] ?? l.status}
                        </span>
                      </td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          {l.status === "draft" && (
                            <Button size="sm" variant="secondary" onClick={() => generatePdf(l.id, l.candidate_name)}>
                              <Download className="mr-1 h-3.5 w-3.5" /> Generate PDF
                            </Button>
                          )}
                          {l.has_pdf && (
                            <>
                              <Button size="sm" variant="secondary" onClick={() => viewPdf(l.id)}>
                                <Eye className="mr-1 h-3.5 w-3.5" /> View PDF
                              </Button>
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={async () => {
                                  const blob = await apiDownload(`/api/v1/offer-letters/${l.id}/pdf`, accessToken);
                                  const url = URL.createObjectURL(blob);
                                  const a = document.createElement("a");
                                  a.href = url;
                                  a.download = `offer-${l.candidate_name.replace(/\s+/g, "-").toLowerCase()}.pdf`;
                                  a.click();
                                  URL.revokeObjectURL(url);
                                }}
                              >
                                <Download className="mr-1 h-3.5 w-3.5" /> Download
                              </Button>
                            </>
                          )}
                          {l.status === "pdf_ready" && (
                            <Button size="sm" onClick={() => releaseMutation.mutate(l.id)} disabled={releaseMutation.isPending}>
                              <Send className="mr-1 h-3.5 w-3.5" /> Release Offer
                            </Button>
                          )}
                          {l.status === "released" && (
                            <span className="text-xs text-green-600">Sent to candidate</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!letters?.length && (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500">
                        No offer letters yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      <Modal
        open={showTemplateModal}
        onClose={() => setShowTemplateModal(false)}
        title={editingTemplate ? "Edit Template" : "Create Template"}
        wide
      >
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            saveTemplateMutation.mutate();
          }}
        >
          <Input
            label="Template Name"
            required
            value={templateForm.name}
            onChange={(e) => setTemplateForm((f) => ({ ...f, name: e.target.value }))}
          />
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="text-sm font-medium text-slate-700">Body</label>
              <button type="button" className="text-xs text-brand-600 hover:underline" onClick={loadSampleBody}>
                Load sample
              </button>
            </div>
            <textarea
              className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm"
              rows={14}
              required
              value={templateForm.body_html}
              onChange={(e) => setTemplateForm((f) => ({ ...f, body_html: e.target.value }))}
              placeholder="Use {{candidate_name}}, {{designation}}, {{ctc}}, etc."
            />
            <p className="mt-1 text-xs text-slate-500">
              Supports plain text or simple HTML. Placeholders: {PLACEHOLDERS.map((p) => `{{${p}}}`).join(", ")}
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={templateForm.is_active}
              onChange={(e) => setTemplateForm((f) => ({ ...f, is_active: e.target.checked }))}
            />
            Active (available when creating offers)
          </label>
          <Button type="submit" disabled={saveTemplateMutation.isPending}>
            {saveTemplateMutation.isPending ? "Saving..." : "Save Template"}
          </Button>
        </form>
      </Modal>
    </div>
  );
}
