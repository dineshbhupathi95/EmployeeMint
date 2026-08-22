import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, FileText, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { useAuthStore } from "@/store/auth";

interface Candidate {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  status: string;
  source: string | null;
  applied_for_designation: string | null;
  expected_ctc: string | null;
  current_company: string | null;
  current_designation: string | null;
  notes: string | null;
  has_resume: boolean;
  employee_id: string | null;
  parsed_profile: Record<string, unknown>;
}

interface Offer {
  id: string;
  status: string;
  designation: string | null;
  ctc: string | null;
  joining_date: string | null;
  has_pdf: boolean;
  employee_id: string | null;
}

interface Template {
  id: string;
  name: string;
}

const STATUSES = [
  "new", "screening", "interview", "selected", "offer_draft",
  "offer_sent", "offer_accepted", "offer_declined", "rejected", "withdrawn", "hired",
];

export function CandidateDetailPage() {
  const { candidateId } = useParams<{ candidateId: string }>();
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const resumeRef = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState("");
  const [showOffer, setShowOffer] = useState(false);
  const [showAccept, setShowAccept] = useState<string | null>(null);
  const [offerForm, setOfferForm] = useState({ template_id: "", designation: "", ctc: "", joining_date: "" });
  const [acceptForm, setAcceptForm] = useState({ password: "", start_onboarding: true });

  const { data: candidate, isLoading } = useQuery({
    queryKey: ["candidate", candidateId],
    queryFn: () => apiRequest<Candidate>(`/api/v1/candidates/${candidateId}`, { token: accessToken }),
    enabled: !!candidateId,
  });

  const { data: offers } = useQuery({
    queryKey: ["candidate-offers", candidateId],
    queryFn: () => apiRequest<Offer[]>(`/api/v1/candidates/${candidateId}/offers`, { token: accessToken }),
    enabled: !!candidateId,
  });

  const { data: templates } = useQuery({
    queryKey: ["offer-templates"],
    queryFn: () => apiRequest<Template[]>("/api/v1/offer-letter-templates", { token: accessToken }),
    enabled: showOffer,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["candidate", candidateId] });
    queryClient.invalidateQueries({ queryKey: ["candidate-offers", candidateId] });
    queryClient.invalidateQueries({ queryKey: ["candidates"] });
  };

  const updateStatus = useMutation({
    mutationFn: (status: string) =>
      apiRequest(`/api/v1/candidates/${candidateId}`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => { invalidate(); setMessage("Status updated"); },
    onError: (err: Error) => setMessage(err.message),
  });

  const uploadResume = async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL || ""}/api/v1/candidates/${candidateId}/resume`,
      { method: "POST", headers: { Authorization: `Bearer ${accessToken}` }, body: fd },
    );
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(body?.detail?.error?.message ?? "Upload failed");
    }
    invalidate();
    setMessage("Resume uploaded and fields updated");
  };

  const createOffer = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/candidates/${candidateId}/offers`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          template_id: offerForm.template_id,
          designation: offerForm.designation || null,
          ctc: offerForm.ctc || null,
          joining_date: offerForm.joining_date || null,
        }),
      }),
    onSuccess: () => {
      setShowOffer(false);
      invalidate();
      setMessage("Offer draft created — go to Offer Letters to generate PDF and release");
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const releaseOffer = useMutation({
    mutationFn: async (offerId: string) => {
      await apiRequest(`/api/v1/offer-letters/${offerId}/generate-pdf`, { method: "POST", token: accessToken });
      return apiRequest(`/api/v1/offer-letters/${offerId}/release`, { method: "POST", token: accessToken });
    },
    onSuccess: () => { invalidate(); setMessage("Offer released to candidate"); },
    onError: (err: Error) => setMessage(err.message),
  });

  const acceptOffer = useMutation({
    mutationFn: (offerId: string) =>
      apiRequest<{ employee_id: string; employee_code: string; compensation_configured: boolean }>(
        `/api/v1/candidates/${candidateId}/offers/${offerId}/accept`,
        {
          method: "POST",
          token: accessToken,
          body: JSON.stringify(acceptForm),
        },
      ),
    onSuccess: (result) => {
      setShowAccept(null);
      invalidate();
      setMessage(
        `Hired as ${result.employee_code}. Pay details ${result.compensation_configured ? "configured" : "pending"} in My Pay.`,
      );
    },
    onError: (err: Error) => setMessage(err.message),
  });

  if (isLoading || !candidate) {
    return <p className="text-sm text-slate-500">Loading candidate...</p>;
  }

  const releasedOffer = offers?.find((o) => o.status === "released");

  return (
    <div className="space-y-6">
      <Link to="/app/recruitment" className="inline-flex items-center text-sm text-brand-600 hover:underline">
        <ArrowLeft className="mr-1 h-4 w-4" /> Back to candidates
      </Link>

      <PageHeader
        title={`${candidate.first_name} ${candidate.last_name}`}
        description={candidate.email}
      />

      {message && <p className="rounded-lg bg-brand-50 px-4 py-2 text-sm text-brand-800">{message}</p>}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader title="Profile" />
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <div><dt className="text-slate-500">Phone</dt><dd>{candidate.phone ?? "—"}</dd></div>
              <div><dt className="text-slate-500">Applied for</dt><dd>{candidate.applied_for_designation ?? "—"}</dd></div>
              <div><dt className="text-slate-500">Expected CTC</dt><dd>{candidate.expected_ctc ?? "—"}</dd></div>
              <div><dt className="text-slate-500">Current company</dt><dd>{candidate.current_company ?? "—"}</dd></div>
              <div><dt className="text-slate-500">Current role</dt><dd>{candidate.current_designation ?? "—"}</dd></div>
              <div><dt className="text-slate-500">Source</dt><dd className="capitalize">{candidate.source ?? "—"}</dd></div>
            </dl>
            {candidate.notes && <p className="mt-3 text-sm text-slate-600">{candidate.notes}</p>}
          </Card>

          <Card>
            <CardHeader title="Offers" description="Create offer → Generate PDF → Release → Accept to hire" />
            <div className="mb-3 flex gap-2">
              {candidate.status !== "hired" && (
                <Button size="sm" onClick={() => {
                  setOfferForm({
                    template_id: "",
                    designation: candidate.applied_for_designation ?? "",
                    ctc: candidate.expected_ctc ?? "",
                    joining_date: "",
                  });
                  setShowOffer(true);
                }}>
                  Create Offer
                </Button>
              )}
            </div>
            {offers?.length ? offers.map((o) => (
              <div key={o.id} className="mb-3 rounded-lg border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium capitalize">{o.status.replace(/_/g, " ")}</p>
                    <p className="text-sm text-slate-500">{o.designation} · {o.ctc ?? "CTC TBD"}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {o.status === "draft" && (
                      <Button size="sm" variant="secondary" onClick={() => releaseOffer.mutate(o.id)} disabled={releaseOffer.isPending}>
                        Generate & Release
                      </Button>
                    )}
                    {o.status === "released" && !candidate.employee_id && (
                      <Button size="sm" onClick={() => setShowAccept(o.id)}>
                        <CheckCircle2 className="mr-1 h-4 w-4" /> Accept Offer & Hire
                      </Button>
                    )}
                    {o.has_pdf && (
                      <a href={`/api/v1/offer-letters/${o.id}/pdf`} target="_blank" rel="noreferrer" className="text-sm text-brand-600 hover:underline">
                        View PDF
                      </a>
                    )}
                  </div>
                </div>
              </div>
            )) : (
              <p className="text-sm text-slate-500">No offers yet</p>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader title="Status" />
            <select
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm capitalize"
              value={candidate.status}
              disabled={candidate.status === "hired"}
              onChange={(e) => updateStatus.mutate(e.target.value)}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
              ))}
            </select>
            {candidate.employee_id && (
              <p className="mt-3 text-sm text-green-700">
                Hired — <Link to="/app/employees" className="underline">View employees</Link>
              </p>
            )}
          </Card>

          <Card>
            <CardHeader title="Resume" />
            {candidate.has_resume ? (
              <a
                href={`${import.meta.env.VITE_API_BASE_URL || ""}/api/v1/candidates/${candidateId}/resume`}
                className="text-sm text-brand-600 hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                Download resume
              </a>
            ) : (
              <p className="text-sm text-slate-500">No resume uploaded</p>
            )}
            <input ref={resumeRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadResume(f).catch((err) => setMessage(err.message)); e.target.value = ""; }} />
            <Button className="mt-3 w-full" variant="secondary" size="sm" onClick={() => resumeRef.current?.click()}>
              <Upload className="mr-1 h-4 w-4" /> {candidate.has_resume ? "Replace resume" : "Upload resume"}
            </Button>
          </Card>

          {((candidate.parsed_profile?.skills as string[]) ?? []).length > 0 && (
            <Card>
              <CardHeader title="Parsed skills" />
              <div className="flex flex-wrap gap-1">
                {((candidate.parsed_profile.skills as string[]) ?? []).map((s) => (
                  <span key={s} className="rounded bg-slate-100 px-2 py-0.5 text-xs">{s}</span>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>

      <Modal open={showOffer} onClose={() => setShowOffer(false)} title="Create Offer Letter">
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); createOffer.mutate(); }}>
          <div>
            <label className="mb-1 block text-sm font-medium">Template</label>
            <select className="w-full rounded-lg border px-3 py-2 text-sm" required
              value={offerForm.template_id} onChange={(e) => setOfferForm((f) => ({ ...f, template_id: e.target.value }))}>
              <option value="">Select template</option>
              {templates?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <Input label="Designation" value={offerForm.designation} onChange={(e) => setOfferForm((f) => ({ ...f, designation: e.target.value }))} />
          <Input label="CTC" value={offerForm.ctc} onChange={(e) => setOfferForm((f) => ({ ...f, ctc: e.target.value }))} />
          <Input label="Joining date" type="date" value={offerForm.joining_date} onChange={(e) => setOfferForm((f) => ({ ...f, joining_date: e.target.value }))} />
          <Button type="submit" disabled={createOffer.isPending}>Create Offer Draft</Button>
        </form>
      </Modal>

      <Modal open={!!showAccept} onClose={() => setShowAccept(null)} title="Accept Offer & Create Employee">
        <p className="mb-4 text-sm text-slate-600">
          Creates employee account, links offer letter, sets up My Pay from CTC, and starts onboarding.
        </p>
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); if (showAccept) acceptOffer.mutate(showAccept); }}>
          <Input label="Login password for new employee" type="password" required minLength={8}
            value={acceptForm.password} onChange={(e) => setAcceptForm((f) => ({ ...f, password: e.target.value }))} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={acceptForm.start_onboarding}
              onChange={(e) => setAcceptForm((f) => ({ ...f, start_onboarding: e.target.checked }))} />
            Start onboarding checklist
          </label>
          <Button type="submit" disabled={acceptOffer.isPending}>
            <FileText className="mr-2 h-4 w-4" />
            Accept & Hire
          </Button>
        </form>
        {releasedOffer && (
          <p className="mt-2 text-xs text-slate-500">Offer: {releasedOffer.designation} · {releasedOffer.ctc}</p>
        )}
      </Modal>
    </div>
  );
}
