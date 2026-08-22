import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface Candidate {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  status: string;
  applied_for_designation: string | null;
  expected_ctc: string | null;
  current_company: string | null;
  has_resume: boolean;
  created_at: string;
}

const STATUS_STYLES: Record<string, string> = {
  new: "bg-slate-100 text-slate-700",
  screening: "bg-blue-100 text-blue-800",
  interview: "bg-violet-100 text-violet-800",
  selected: "bg-indigo-100 text-indigo-800",
  offer_draft: "bg-amber-100 text-amber-800",
  offer_sent: "bg-orange-100 text-orange-800",
  offer_accepted: "bg-green-100 text-green-800",
  hired: "bg-green-100 text-green-900",
  rejected: "bg-red-100 text-red-800",
  withdrawn: "bg-slate-100 text-slate-600",
};

const STATUS_FILTERS = ["", "new", "screening", "interview", "selected", "offer_sent", "hired", "rejected"];

export function CandidatesPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    applied_for_designation: "",
    expected_ctc: "",
    current_company: "",
    source: "direct",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["candidates", statusFilter],
    queryFn: () => {
      const q = statusFilter ? `?status=${statusFilter}` : "";
      return apiRequest<{ items: Candidate[]; total: number }>(`/api/v1/candidates${q}`, { token: accessToken });
    },
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<Candidate>("/api/v1/candidates", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify(form),
      }),
    onSuccess: async (candidate) => {
      queryClient.invalidateQueries({ queryKey: ["candidates"] });
      setShowCreate(false);
      setMessage(`Candidate ${candidate.first_name} created`);
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const handleResumeParse = async (file: File) => {
    if (!file.size) {
      setMessage("Selected file is empty");
      return;
    }
    const fd = new FormData();
    fd.append("file", file, file.name);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || ""}/api/v1/candidates/parse-resume`,
        { method: "POST", headers: { Authorization: `Bearer ${accessToken}` }, body: fd },
      );
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        const msg =
          body?.detail?.error?.message ??
          body?.error?.message ??
          (typeof body?.detail === "string" ? body.detail : null) ??
          "Could not parse resume";
        throw new Error(msg);
      }
      const parsed = body;
      setForm((f) => ({
        ...f,
        first_name: parsed.first_name || f.first_name,
        last_name: parsed.last_name || f.last_name,
        email: parsed.email || f.email,
        phone: parsed.phone || f.phone,
        current_company: parsed.current_company || f.current_company,
        applied_for_designation: parsed.current_designation || f.applied_for_designation,
      }));
      setMessage(
        parsed.parse_warning
          ? `Resume parsed with note: ${parsed.parse_warning}`
          : "Resume parsed — review and save candidate details",
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Parse failed");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recruitment"
        description="Manage candidates, resumes, offers, and hire-to-employee flow"
        action={
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Candidate
          </Button>
        }
      />

      {message && <p className="rounded-lg bg-brand-50 px-4 py-2 text-sm text-brand-800">{message}</p>}

      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Search className="h-4 w-4 text-slate-400" />
          {STATUS_FILTERS.map((s) => (
            <button
              key={s || "all"}
              type="button"
              onClick={() => setStatusFilter(s)}
              className={cn(
                "rounded-full px-3 py-1 text-xs font-medium capitalize",
                statusFilter === s ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200",
              )}
            >
              {s || "All"}
            </button>
          ))}
        </div>

        {isLoading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="em-table text-sm">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role applied</th>
                  <th>Status</th>
                  <th>Resume</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((c) => (
                  <tr key={c.id}>
                    <td className="font-medium">{c.first_name} {c.last_name}</td>
                    <td>{c.email}</td>
                    <td>{c.applied_for_designation ?? "—"}</td>
                    <td>
                      <span className={cn("rounded-full px-2 py-0.5 text-xs capitalize", STATUS_STYLES[c.status] ?? STATUS_STYLES.new)}>
                        {c.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td>{c.has_resume ? "Yes" : "—"}</td>
                    <td>
                      <Link to={`/app/recruitment/${c.id}`} className="text-brand-600 hover:underline">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
                {!data?.items.length && (
                  <tr><td colSpan={6} className="py-8 text-center text-slate-500">No candidates yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="New Candidate" wide>
        <div className="mb-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
          <p className="mb-2 text-sm font-medium text-slate-700">Upload resume to auto-fill</p>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleResumeParse(file);
              e.target.value = "";
            }}
          />
          <Button variant="secondary" type="button" onClick={() => fileRef.current?.click()}>
            <Upload className="mr-2 h-4 w-4" />
            Upload & Parse Resume
          </Button>
        </div>
        <form
          className="grid gap-3 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
        >
          <Input label="First name" required value={form.first_name} onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))} />
          <Input label="Last name" required value={form.last_name} onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))} />
          <Input label="Email" type="email" required value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
          <Input label="Phone" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} />
          <Input label="Applied for" value={form.applied_for_designation} onChange={(e) => setForm((f) => ({ ...f, applied_for_designation: e.target.value }))} />
          <Input label="Expected CTC" placeholder="e.g. 12 LPA" value={form.expected_ctc} onChange={(e) => setForm((f) => ({ ...f, expected_ctc: e.target.value }))} />
          <Input label="Current company" className="sm:col-span-2" value={form.current_company} onChange={(e) => setForm((f) => ({ ...f, current_company: e.target.value }))} />
          <div className="sm:col-span-2 flex gap-2">
            <Button type="submit" disabled={createMutation.isPending}>Save Candidate</Button>
            <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
