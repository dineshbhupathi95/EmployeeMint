import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, CheckCircle2, Download, Eye, FileUp, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { apiDownload, apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { UserAvatar } from "@/components/UserAvatar";
import { cn } from "@/lib/utils";
import { useAuthStore, type UserInfo } from "@/store/auth";
import { THEMES, useThemeStore } from "@/store/theme";
import { EmployeeBackgroundDetails } from "@/features/profile/EmployeeBackgroundDetails";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

function parseApiError(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const b = body as Record<string, unknown>;
  const detail = b.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const err = (detail as Record<string, unknown>).error;
    if (err && typeof err === "object" && typeof (err as { message?: unknown }).message === "string") {
      return (err as { message: string }).message;
    }
  }
  if (b.error && typeof b.error === "object" && typeof (b.error as { message?: unknown }).message === "string") {
    return (b.error as { message: string }).message;
  }
  if (typeof detail === "string") return detail;
  return fallback;
}

interface DocType {
  code: string;
  label: string;
  description: string;
}

interface EmpDocument {
  id: string;
  document_type: string;
  title: string;
  file_name: string;
  content_type: string | null;
  file_size: number;
  status: string;
  created_at: string | null;
}

interface OnboardingTask {
  id: string;
  title: string;
  description: string | null;
  status: string;
  due_date: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  in_progress: "bg-brand-100 text-brand-800",
  completed: "bg-green-100 text-green-800",
};

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function isImageDoc(doc: Pick<EmpDocument, "content_type" | "file_name">) {
  const ct = (doc.content_type || "").toLowerCase();
  if (ct.startsWith("image/")) return true;
  return /\.(jpe?g|png|gif|webp|bmp)$/i.test(doc.file_name);
}

function isPdfDoc(doc: Pick<EmpDocument, "content_type" | "file_name">) {
  const ct = (doc.content_type || "").toLowerCase();
  if (ct.includes("pdf")) return true;
  return /\.pdf$/i.test(doc.file_name);
}

function isPreviewable(doc: Pick<EmpDocument, "content_type" | "file_name">) {
  return isImageDoc(doc) || isPdfDoc(doc);
}

export function ProfilePage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const queryClient = useQueryClient();

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () =>
      apiRequest<UserInfo>("/api/v1/auth/me", { token: accessToken }),
  });

  useEffect(() => {
    if (me) setUser(me);
  }, [me, setUser]);

  const avatarInputRef = useRef<HTMLInputElement>(null);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [avatarError, setAvatarError] = useState("");
  const [avatarMessage, setAvatarMessage] = useState("");

  const { data: docTypes } = useQuery({
    queryKey: ["document-types"],
    queryFn: () => apiRequest<DocType[]>("/api/v1/documents/types", { token: accessToken }),
  });

  const { data: documents, refetch: refetchDocs } = useQuery({
    queryKey: ["my-documents"],
    queryFn: () => apiRequest<EmpDocument[]>("/api/v1/documents/my", { token: accessToken }),
  });

  const { data: myTasks, refetch: refetchTasks } = useQuery({
    queryKey: ["my-onboarding-tasks"],
    queryFn: () =>
      apiRequest<OnboardingTask[]>("/api/v1/onboarding/my-tasks", { token: accessToken }),
  });

  const [form, setForm] = useState({ first_name: "", last_name: "", phone: "", work_email: "" });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [docMessage, setDocMessage] = useState("");
  const [docError, setDocError] = useState("");
  const [uploadType, setUploadType] = useState("identity_proof");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<{
    doc: EmpDocument;
    url: string;
  } | null>(null);
  const [previewLoadingId, setPreviewLoadingId] = useState<string | null>(null);

  const closePreview = () => {
    if (preview?.url) URL.revokeObjectURL(preview.url);
    setPreview(null);
  };

  useEffect(() => {
    if (me?.full_name) {
      const parts = me.full_name.split(" ");
      setForm({
        first_name: parts[0] ?? "",
        last_name: parts.slice(1).join(" "),
        phone: me.phone ?? "",
        work_email: me.work_email ?? "",
      });
    }
  }, [me]);

  useEffect(() => {
    if (docTypes?.length && !docTypes.some((t) => t.code === uploadType)) {
      setUploadType(docTypes[0].code);
    }
  }, [docTypes, uploadType]);

  const saveMutation = useMutation<UserInfo, Error>({
    mutationFn: () =>
      apiRequest<UserInfo>("/api/v1/auth/me", {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({
          first_name: form.first_name,
          last_name: form.last_name,
          phone: form.phone || null,
          work_email: form.work_email || null,
        }),
      }),
    onSuccess: (user: UserInfo) => {
      setUser(user);
      setSaved(true);
      setError("");
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (err: Error) => setError(err.message),
  });

  const completeTaskMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiRequest(`/api/v1/onboarding/my-tasks/${id}`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-onboarding-tasks"] });
    },
  });

  const deleteDocMutation = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`/api/v1/documents/my/${id}`, { method: "DELETE", token: accessToken }),
    onSuccess: () => {
      refetchDocs();
      setDocMessage("Document removed.");
    },
    onError: (err: Error) => setDocError(err.message),
  });

  const uploadDocument = async () => {
    if (!uploadFile) {
      setDocError("Choose a file to upload");
      return;
    }
    setUploading(true);
    setDocError("");
    setDocMessage("");
    const body = new FormData();
    body.append("document_type", uploadType);
    body.append("file", uploadFile);
    try {
      const res = await fetch(`${API_BASE}/api/v1/documents/my`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(parseApiError(err, res.statusText || "Request failed"));
      }
      const data = (await res.json()) as { message?: string };
      setDocMessage(data.message || "Document uploaded.");
      setUploadFile(null);
      await refetchDocs();
      await refetchTasks();
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    } catch (err) {
      setDocError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const downloadDocument = async (id: string, fileName: string) => {
    try {
      const blob = await apiDownload(`/api/v1/documents/my/${id}/download`, accessToken);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setDocError(err instanceof Error ? err.message : "Download failed");
    }
  };

  const viewDocument = async (doc: EmpDocument) => {
    setPreviewLoadingId(doc.id);
    setDocError("");
    try {
      const blob = await apiDownload(`/api/v1/documents/my/${doc.id}/download`, accessToken);
      // Ensure browser can render images/PDFs even if server content-type is missing
      let typed = blob;
      if (isPdfDoc(doc) && blob.type !== "application/pdf") {
        typed = new Blob([blob], { type: "application/pdf" });
      } else if (isImageDoc(doc) && !blob.type.startsWith("image/")) {
        const ext = doc.file_name.split(".").pop()?.toLowerCase();
        const map: Record<string, string> = {
          jpg: "image/jpeg",
          jpeg: "image/jpeg",
          png: "image/png",
          gif: "image/gif",
          webp: "image/webp",
        };
        typed = new Blob([blob], { type: map[ext || ""] || "image/jpeg" });
      }
      if (preview?.url) URL.revokeObjectURL(preview.url);
      setPreview({ doc, url: URL.createObjectURL(typed) });
    } catch (err) {
      setDocError(err instanceof Error ? err.message : "Unable to open file");
    } finally {
      setPreviewLoadingId(null);
    }
  };

  const pendingTasks = myTasks?.filter((t) => t.status !== "completed") ?? [];
  const completedTasks = myTasks?.filter((t) => t.status === "completed") ?? [];
  const selectedType = docTypes?.find((t) => t.code === uploadType);

  const uploadAvatar = async (file: File | null) => {
    if (!file) return;
    setAvatarBusy(true);
    setAvatarError("");
    setAvatarMessage("");
    const body = new FormData();
    body.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/me/avatar`, {
        method: "POST",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(parseApiError(err, res.statusText || "Request failed"));
      }
      const user = (await res.json()) as UserInfo;
      setUser(user);
      queryClient.setQueryData(["me"], user);
      setAvatarMessage("Profile photo updated.");
    } catch (err) {
      setAvatarError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setAvatarBusy(false);
      if (avatarInputRef.current) avatarInputRef.current.value = "";
    }
  };

  const removeAvatar = async () => {
    setAvatarBusy(true);
    setAvatarError("");
    setAvatarMessage("");
    try {
      const user = await apiRequest<UserInfo>("/api/v1/auth/me/avatar", {
        method: "DELETE",
        token: accessToken,
      });
      setUser(user);
      queryClient.setQueryData(["me"], user);
      setAvatarMessage("Profile photo removed.");
    } catch (err) {
      setAvatarError(err instanceof Error ? err.message : "Could not remove photo");
    } finally {
      setAvatarBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader title="My Profile" description="Personal info, education, work history, onboarding, and documents" />

      <Card>
        <CardHeader title="Profile photo" description="Shown on your profile and in the top bar" />
        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <UserAvatar size="xl" className="ring-4 ring-brand-50" />
          <div className="min-w-0 space-y-3">
            <p className="text-sm text-slate-600">
              JPG, PNG, or WebP · max 2MB
            </p>
            <input
              ref={avatarInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
              className="hidden"
              onChange={(e) => uploadAvatar(e.target.files?.[0] ?? null)}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                disabled={avatarBusy}
                onClick={() => avatarInputRef.current?.click()}
              >
                <Camera className="mr-1.5 h-4 w-4" />
                {avatarBusy ? "Uploading…" : me?.has_avatar ? "Change photo" : "Upload photo"}
              </Button>
              {me?.has_avatar && (
                <Button type="button" variant="secondary" disabled={avatarBusy} onClick={removeAvatar}>
                  <Trash2 className="mr-1.5 h-4 w-4" />
                  Remove
                </Button>
              )}
            </div>
            {avatarError && <p className="text-sm text-red-600">{avatarError}</p>}
            {avatarMessage && <p className="text-sm text-green-600">{avatarMessage}</p>}
          </div>
        </div>
      </Card>

      {(myTasks?.length ?? 0) > 0 && (
        <Card>
          <CardHeader
            title="My Onboarding"
            description={
              pendingTasks.length
                ? `${pendingTasks.length} task${pendingTasks.length === 1 ? "" : "s"} remaining — upload documents below or mark complete`
                : "All onboarding tasks completed"
            }
          />
          <ul className="space-y-3">
            {[...pendingTasks, ...completedTasks].map((task) => (
              <li
                key={task.id}
                className="flex flex-col gap-2 rounded-lg border border-slate-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium text-slate-900">{task.title}</p>
                    <span
                      className={cn(
                        "rounded-md px-2 py-0.5 text-xs font-medium capitalize",
                        STATUS_STYLES[task.status] ?? "bg-slate-100 text-slate-700",
                      )}
                    >
                      {task.status.replace("_", " ")}
                    </span>
                  </div>
                  {task.description && (
                    <p className="mt-0.5 text-sm text-slate-500">{task.description}</p>
                  )}
                  {task.due_date && (
                    <p className="mt-1 text-xs text-slate-400">Due {task.due_date}</p>
                  )}
                </div>
                {task.status !== "completed" && (
                  <div className="flex shrink-0 gap-2">
                    {task.status === "pending" && (
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() =>
                          completeTaskMutation.mutate({ id: task.id, status: "in_progress" })
                        }
                      >
                        Start
                      </Button>
                    )}
                    <Button
                      type="button"
                      onClick={() =>
                        completeTaskMutation.mutate({ id: task.id, status: "completed" })
                      }
                    >
                      <CheckCircle2 className="mr-1.5 h-4 w-4" />
                      Complete
                    </Button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card>
        <CardHeader
          title="Documents"
          description="Identity, bank, tax, and other required uploads for onboarding and payroll"
        />
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Document type</label>
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={uploadType}
                onChange={(e) => setUploadType(e.target.value)}
              >
                {(docTypes ?? []).map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.label}
                  </option>
                ))}
              </select>
              {selectedType && (
                <p className="mt-1 text-xs text-slate-500">{selectedType.description}</p>
              )}
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">File</label>
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx"
                className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-brand-700"
                onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              />
              <p className="mt-1 text-xs text-slate-400">PDF or image, max 8MB</p>
            </div>
          </div>
          {docError && <p className="text-sm text-red-600">{docError}</p>}
          {docMessage && <p className="text-sm text-green-600">{docMessage}</p>}
          <Button type="button" disabled={uploading || !uploadFile} onClick={uploadDocument}>
            <FileUp className="mr-1.5 h-4 w-4" />
            {uploading ? "Uploading..." : "Upload document"}
          </Button>

          <div className="border-t border-slate-100 pt-4">
            <p className="mb-3 text-sm font-medium text-slate-700">Uploaded files</p>
            {!documents?.length ? (
              <p className="text-sm text-slate-500">No documents uploaded yet.</p>
            ) : (
              <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                {documents.map((doc) => {
                  const typeLabel =
                    docTypes?.find((t) => t.code === doc.document_type)?.label ?? doc.document_type;
                  const canPreview = isPreviewable(doc);
                  return (
                    <li
                      key={doc.id}
                      className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <DocumentThumb
                          doc={doc}
                          token={accessToken}
                          onOpen={() => viewDocument(doc)}
                        />
                        <div className="min-w-0">
                          <button
                            type="button"
                            className={cn(
                              "truncate text-left font-medium text-slate-900",
                              canPreview && "hover:text-brand-700 hover:underline",
                            )}
                            onClick={() => canPreview && viewDocument(doc)}
                          >
                            {doc.title}
                          </button>
                          <p className="text-xs text-slate-500">
                            {typeLabel} · {doc.file_name} · {formatBytes(doc.file_size)}
                          </p>
                        </div>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={previewLoadingId === doc.id}
                          onClick={() => viewDocument(doc)}
                          title="View"
                        >
                          <Eye className="h-4 w-4" />
                          <span className="ml-1.5 hidden sm:inline">
                            {previewLoadingId === doc.id ? "Opening…" : "View"}
                          </span>
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => downloadDocument(doc.id, doc.file_name)}
                          title="Download"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => deleteDocMutation.mutate(doc.id)}
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      </Card>

      <Modal open={!!preview} onClose={closePreview} title={preview?.doc.title || "Document"} wide>
        {preview && (
          <div className="space-y-4">
            <p className="text-sm text-slate-500">{preview.doc.file_name}</p>
            {isImageDoc(preview.doc) ? (
              <div className="overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-2">
                <img
                  src={preview.url}
                  alt={preview.doc.title}
                  className="mx-auto max-h-[70vh] w-auto max-w-full object-contain"
                />
              </div>
            ) : isPdfDoc(preview.doc) ? (
              <iframe
                title={preview.doc.title}
                src={preview.url}
                className="h-[70vh] w-full rounded-lg border border-slate-200 bg-white"
              />
            ) : (
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-10 text-center">
                <p className="text-sm text-slate-600">
                  Preview is not available for this file type. Download to open it on your device.
                </p>
                <Button
                  type="button"
                  className="mt-4"
                  onClick={() => downloadDocument(preview.doc.id, preview.doc.file_name)}
                >
                  <Download className="mr-1.5 h-4 w-4" />
                  Download
                </Button>
              </div>
            )}
          </div>
        )}
      </Modal>

      <Card>
        <CardHeader title="Personal Information" />
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            saveMutation.mutate();
          }}
        >
          <Input label="Login Email" value={me?.email ?? ""} disabled />
          {me?.employee_code && <Input label="Employee ID" value={me.employee_code} disabled />}
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="First Name"
              required
              value={form.first_name}
              onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
            />
            <Input
              label="Last Name"
              required
              value={form.last_name}
              onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
            />
          </div>
          <Input
            label="Work Email"
            type="email"
            value={form.work_email}
            onChange={(e) => setForm((f) => ({ ...f, work_email: e.target.value }))}
          />
          <Input
            label="Phone"
            value={form.phone}
            onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          {saved && <p className="text-sm text-green-600">Profile updated successfully.</p>}
          <Button type="submit" disabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Saving..." : "Save Profile"}
          </Button>
        </form>
      </Card>

      {me?.employee_id && <EmployeeBackgroundDetails mode="own" />}

      <Card>
        <CardHeader title="Appearance" description="Choose your preferred accent color" />
        <div className="flex flex-wrap gap-3">
          {THEMES.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTheme(t.id)}
              className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-sm transition-colors ${
                theme === t.id
                  ? "border-brand-600 bg-brand-50 text-brand-700"
                  : "border-slate-200 hover:bg-slate-50"
              }`}
            >
              <span className="h-4 w-4 rounded-full" style={{ backgroundColor: t.swatch }} />
              {t.label}
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}

function DocumentThumb({
  doc,
  token,
  onOpen,
}: {
  doc: EmpDocument;
  token: string | null;
  onOpen: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!isImageDoc(doc)) return;
    let active = true;
    let objectUrl: string | null = null;
    apiDownload(`/api/v1/documents/my/${doc.id}/download`, token)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        /* thumbnail optional */
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [doc.id, doc.content_type, doc.file_name, token]);

  if (url) {
    return (
      <button
        type="button"
        onClick={onOpen}
        className="h-14 w-14 shrink-0 overflow-hidden rounded-lg border border-slate-200 bg-slate-50"
        title="View"
      >
        <img src={url} alt="" className="h-full w-full object-cover" />
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-xs font-medium uppercase text-slate-500"
      title="View"
    >
      {isPdfDoc(doc) ? "PDF" : "FILE"}
    </button>
  );
}

