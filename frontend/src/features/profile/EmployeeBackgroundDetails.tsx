import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Eye, Plus, Trash2 } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { apiDownload, apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { useAuthStore } from "@/store/auth";
import { usePermission } from "@/hooks/usePermission";

export interface Education {
  id: string;
  degree: string;
  institution: string;
  field_of_study: string | null;
  year_of_passing: number | null;
  grade_or_percentage: string | null;
  notes: string | null;
}

export interface WorkExperience {
  id: string;
  company_name: string;
  designation: string;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  location: string | null;
  last_drawn_salary: string | null;
  reason_for_leaving: string | null;
  responsibilities: string | null;
}

export interface EmpDoc {
  id: string;
  document_type: string;
  title: string;
  file_name: string;
  content_type?: string | null;
  file_size?: number;
  status: string;
  created_at: string | null;
}

export interface EmployeeDetails {
  employee_id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  work_email: string | null;
  phone: string | null;
  date_of_joining: string | null;
  date_of_birth: string | null;
  gender: string | null;
  marital_status: string | null;
  blood_group: string | null;
  nationality: string | null;
  personal_email: string | null;
  father_name: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  emergency_contact_relation: string | null;
  current_address: string | null;
  permanent_address: string | null;
  pan_number: string | null;
  aadhaar_number: string | null;
  passport_number: string | null;
  background_verification_status: string | null;
  background_verification_notes: string | null;
  educations: Education[];
  work_experiences: WorkExperience[];
  documents: EmpDoc[];
}

type PersonalForm = {
  date_of_birth: string;
  gender: string;
  marital_status: string;
  blood_group: string;
  nationality: string;
  personal_email: string;
  father_name: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  emergency_contact_relation: string;
  current_address: string;
  permanent_address: string;
  pan_number: string;
  aadhaar_number: string;
  passport_number: string;
};

const emptyPersonal = (): PersonalForm => ({
  date_of_birth: "",
  gender: "",
  marital_status: "",
  blood_group: "",
  nationality: "",
  personal_email: "",
  father_name: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  emergency_contact_relation: "",
  current_address: "",
  permanent_address: "",
  pan_number: "",
  aadhaar_number: "",
  passport_number: "",
});

const emptyEducation = {
  degree: "",
  institution: "",
  field_of_study: "",
  year_of_passing: "",
  grade_or_percentage: "",
  notes: "",
};

const emptyExperience = {
  company_name: "",
  designation: "",
  start_date: "",
  end_date: "",
  is_current: false,
  location: "",
  last_drawn_salary: "",
  reason_for_leaving: "",
  responsibilities: "",
};

const BG_STATUSES = [
  { value: "pending", label: "Pending" },
  { value: "in_progress", label: "In progress" },
  { value: "cleared", label: "Cleared" },
  { value: "failed", label: "Failed" },
  { value: "not_required", label: "Not required" },
];

function detailsApiBase(mode: "own" | "hr", employeeId?: string) {
  if (mode === "own") return "/api/v1/employee-details/my";
  return `/api/v1/employee-details/employee/${employeeId}`;
}

function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <label className="mb-1.5 block text-sm font-medium text-slate-700">{label}</label>
      {children}
    </div>
  );
}

function selectClass() {
  return "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm";
}

function textareaClass() {
  return "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm";
}

export function EmployeeBackgroundDetails({
  mode,
  employeeId,
}: {
  mode: "own" | "hr";
  employeeId?: string;
}) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const canEditAll = usePermission("employee.edit.all");
  const canEditOwn = usePermission("employee.edit.own");
  const canEdit = mode === "own" ? canEditOwn : canEditAll;
  const canHrVerify = mode === "hr" && canEditAll;

  const queryKey = mode === "own" ? ["employee-details", "my"] : ["employee-details", employeeId];
  const base = detailsApiBase(mode, employeeId);

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () =>
      apiRequest<EmployeeDetails>(
        mode === "own" ? "/api/v1/employee-details/my" : `/api/v1/employee-details/employee/${employeeId}`,
        { token: accessToken },
      ),
    enabled: mode === "own" || !!employeeId,
  });

  const [personal, setPersonal] = useState<PersonalForm>(emptyPersonal());
  const [personalMsg, setPersonalMsg] = useState("");
  const [personalErr, setPersonalErr] = useState("");
  const [eduModal, setEduModal] = useState(false);
  const [expModal, setExpModal] = useState(false);
  const [eduForm, setEduForm] = useState(emptyEducation);
  const [expForm, setExpForm] = useState(emptyExperience);
  const [formErr, setFormErr] = useState("");
  const [verifyStatus, setVerifyStatus] = useState("");
  const [verifyNotes, setVerifyNotes] = useState("");
  const [verifyMsg, setVerifyMsg] = useState("");
  const [preview, setPreview] = useState<{ doc: EmpDoc; url: string } | null>(null);

  useEffect(() => {
    if (!data) return;
    setPersonal({
      date_of_birth: data.date_of_birth ?? "",
      gender: data.gender ?? "",
      marital_status: data.marital_status ?? "",
      blood_group: data.blood_group ?? "",
      nationality: data.nationality ?? "",
      personal_email: data.personal_email ?? "",
      father_name: data.father_name ?? "",
      emergency_contact_name: data.emergency_contact_name ?? "",
      emergency_contact_phone: data.emergency_contact_phone ?? "",
      emergency_contact_relation: data.emergency_contact_relation ?? "",
      current_address: data.current_address ?? "",
      permanent_address: data.permanent_address ?? "",
      pan_number: data.pan_number ?? "",
      aadhaar_number: data.aadhaar_number ?? "",
      passport_number: data.passport_number ?? "",
    });
    setVerifyStatus(data.background_verification_status ?? "pending");
    setVerifyNotes(data.background_verification_notes ?? "");
  }, [data]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey });

  const savePersonal = useMutation({
    mutationFn: () =>
      apiRequest<EmployeeDetails>(`${base}/personal`, {
        method: "PUT",
        token: accessToken,
        body: JSON.stringify({
          date_of_birth: personal.date_of_birth || null,
          gender: personal.gender || null,
          marital_status: personal.marital_status || null,
          blood_group: personal.blood_group || null,
          nationality: personal.nationality || null,
          personal_email: personal.personal_email || null,
          father_name: personal.father_name || null,
          emergency_contact_name: personal.emergency_contact_name || null,
          emergency_contact_phone: personal.emergency_contact_phone || null,
          emergency_contact_relation: personal.emergency_contact_relation || null,
          current_address: personal.current_address || null,
          permanent_address: personal.permanent_address || null,
          pan_number: personal.pan_number || null,
          aadhaar_number: personal.aadhaar_number || null,
          passport_number: personal.passport_number || null,
        }),
      }),
    onSuccess: () => {
      setPersonalMsg("Personal details saved.");
      setPersonalErr("");
      invalidate();
      setTimeout(() => setPersonalMsg(""), 3000);
    },
    onError: (e: Error) => setPersonalErr(e.message),
  });

  const saveVerify = useMutation({
    mutationFn: () =>
      apiRequest<EmployeeDetails>(
        `/api/v1/employee-details/employee/${employeeId}/verification`,
        {
          method: "PUT",
          token: accessToken,
          body: JSON.stringify({
            background_verification_status: verifyStatus || null,
            background_verification_notes: verifyNotes || null,
          }),
        },
      ),
    onSuccess: () => {
      setVerifyMsg("Verification status updated.");
      invalidate();
      setTimeout(() => setVerifyMsg(""), 3000);
    },
  });

  const addEducation = useMutation({
    mutationFn: () =>
      apiRequest(`${base}/education`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          degree: eduForm.degree,
          institution: eduForm.institution,
          field_of_study: eduForm.field_of_study || null,
          year_of_passing: eduForm.year_of_passing ? Number(eduForm.year_of_passing) : null,
          grade_or_percentage: eduForm.grade_or_percentage || null,
          notes: eduForm.notes || null,
        }),
      }),
    onSuccess: () => {
      setEduModal(false);
      setEduForm(emptyEducation);
      setFormErr("");
      invalidate();
    },
    onError: (e: Error) => setFormErr(e.message),
  });

  const deleteEducation = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`${base}/education/${id}`, { method: "DELETE", token: accessToken }),
    onSuccess: invalidate,
  });

  const addExperience = useMutation({
    mutationFn: () =>
      apiRequest(`${base}/experience`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          company_name: expForm.company_name,
          designation: expForm.designation,
          start_date: expForm.start_date || null,
          end_date: expForm.is_current ? null : expForm.end_date || null,
          is_current: expForm.is_current,
          location: expForm.location || null,
          last_drawn_salary: expForm.last_drawn_salary || null,
          reason_for_leaving: expForm.reason_for_leaving || null,
          responsibilities: expForm.responsibilities || null,
        }),
      }),
    onSuccess: () => {
      setExpModal(false);
      setExpForm(emptyExperience);
      setFormErr("");
      invalidate();
    },
    onError: (e: Error) => setFormErr(e.message),
  });

  const deleteExperience = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`${base}/experience/${id}`, { method: "DELETE", token: accessToken }),
    onSuccess: invalidate,
  });

  const openDoc = async (doc: EmpDoc) => {
    const path =
      mode === "own"
        ? `/api/v1/documents/my/${doc.id}/download`
        : `/api/v1/employee-details/employee/${employeeId}/documents/${doc.id}/download`;
    const blob = await apiDownload(path, accessToken);
    const url = URL.createObjectURL(blob);
    setPreview({ doc, url });
  };

  const downloadDoc = async (doc: EmpDoc) => {
    const path =
      mode === "own"
        ? `/api/v1/documents/my/${doc.id}/download`
        : `/api/v1/employee-details/employee/${employeeId}/documents/${doc.id}/download`;
    const blob = await apiDownload(path, accessToken);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = doc.file_name;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return <p className="text-sm text-slate-500">Loading details…</p>;
  }

  if (!data) {
    return <p className="text-sm text-slate-500">Unable to load employee details.</p>;
  }

  return (
    <div className="space-y-6">
      {mode === "hr" && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="font-medium text-slate-900">
            {data.first_name} {data.last_name}
          </p>
          <p className="text-sm text-slate-500">
            {data.employee_code}
            {data.work_email ? ` · ${data.work_email}` : ""}
            {data.phone ? ` · ${data.phone}` : ""}
          </p>
        </div>
      )}

      {canHrVerify && (
        <Card>
          <CardHeader
            title="Background verification"
            description="HR status for document and history checks"
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Status">
              <select
                className={selectClass()}
                value={verifyStatus}
                onChange={(e) => setVerifyStatus(e.target.value)}
              >
                {BG_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Notes" className="sm:col-span-2">
              <textarea
                className={textareaClass()}
                rows={2}
                value={verifyNotes}
                onChange={(e) => setVerifyNotes(e.target.value)}
                placeholder="Verification agency, findings, follow-ups…"
              />
            </Field>
          </div>
          {verifyMsg && <p className="mt-2 text-sm text-green-600">{verifyMsg}</p>}
          <Button type="button" className="mt-3" onClick={() => saveVerify.mutate()} disabled={saveVerify.isPending}>
            {saveVerify.isPending ? "Saving…" : "Update verification"}
          </Button>
        </Card>
      )}

      {mode === "hr" && data.background_verification_status && !canHrVerify && (
        <p className="text-sm text-slate-600">
          Verification:{" "}
          <span className="font-medium capitalize">
            {data.background_verification_status.replace("_", " ")}
          </span>
        </p>
      )}

      <Card>
        <CardHeader
          title="Personal & identity"
          description="Required for HR records, emergency contact, and background checks"
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Date of birth"
            type="date"
            value={personal.date_of_birth}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, date_of_birth: e.target.value }))}
          />
          <Field label="Gender">
            <select
              className={selectClass()}
              value={personal.gender}
              disabled={!canEdit}
              onChange={(e) => setPersonal((p) => ({ ...p, gender: e.target.value }))}
            >
              <option value="">Select</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
              <option value="prefer_not_to_say">Prefer not to say</option>
            </select>
          </Field>
          <Field label="Marital status">
            <select
              className={selectClass()}
              value={personal.marital_status}
              disabled={!canEdit}
              onChange={(e) => setPersonal((p) => ({ ...p, marital_status: e.target.value }))}
            >
              <option value="">Select</option>
              <option value="single">Single</option>
              <option value="married">Married</option>
              <option value="divorced">Divorced</option>
              <option value="widowed">Widowed</option>
            </select>
          </Field>
          <Input
            label="Blood group"
            value={personal.blood_group}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, blood_group: e.target.value }))}
            placeholder="e.g. O+"
          />
          <Input
            label="Nationality"
            value={personal.nationality}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, nationality: e.target.value }))}
          />
          <Input
            label="Personal email"
            type="email"
            value={personal.personal_email}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, personal_email: e.target.value }))}
          />
          <Input
            label="Father's / guardian name"
            value={personal.father_name}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, father_name: e.target.value }))}
          />
          <Input
            label="PAN"
            value={personal.pan_number}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, pan_number: e.target.value.toUpperCase() }))}
          />
          <Input
            label="Aadhaar"
            value={personal.aadhaar_number}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, aadhaar_number: e.target.value }))}
          />
          <Input
            label="Passport"
            value={personal.passport_number}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, passport_number: e.target.value.toUpperCase() }))}
          />
          <Input
            label="Emergency contact name"
            value={personal.emergency_contact_name}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, emergency_contact_name: e.target.value }))}
          />
          <Input
            label="Emergency contact phone"
            value={personal.emergency_contact_phone}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, emergency_contact_phone: e.target.value }))}
          />
          <Input
            label="Emergency contact relation"
            value={personal.emergency_contact_relation}
            disabled={!canEdit}
            onChange={(e) => setPersonal((p) => ({ ...p, emergency_contact_relation: e.target.value }))}
          />
          <Field label="Current address" className="sm:col-span-2">
            <textarea
              className={textareaClass()}
              rows={2}
              disabled={!canEdit}
              value={personal.current_address}
              onChange={(e) => setPersonal((p) => ({ ...p, current_address: e.target.value }))}
            />
          </Field>
          <Field label="Permanent address" className="sm:col-span-2">
            <textarea
              className={textareaClass()}
              rows={2}
              disabled={!canEdit}
              value={personal.permanent_address}
              onChange={(e) => setPersonal((p) => ({ ...p, permanent_address: e.target.value }))}
            />
          </Field>
        </div>
        {personalErr && <p className="mt-2 text-sm text-red-600">{personalErr}</p>}
        {personalMsg && <p className="mt-2 text-sm text-green-600">{personalMsg}</p>}
        {canEdit && (
          <Button
            type="button"
            className="mt-4"
            disabled={savePersonal.isPending}
            onClick={() => savePersonal.mutate()}
          >
            {savePersonal.isPending ? "Saving…" : "Save personal details"}
          </Button>
        )}
      </Card>

      <Card>
        <CardHeader
          title="Academic details"
          description="Degrees and institutions — used for background verification"
          action={
            canEdit ? (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => {
                  setEduForm(emptyEducation);
                  setFormErr("");
                  setEduModal(true);
                }}
              >
                <Plus className="mr-1 h-4 w-4" />
                Add
              </Button>
            ) : undefined
          }
        />
        {!data.educations.length ? (
          <p className="text-sm text-slate-500">No academic records yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
            {data.educations.map((e) => (
              <li key={e.id} className="flex items-start justify-between gap-3 px-4 py-3">
                <div>
                  <p className="font-medium text-slate-900">{e.degree}</p>
                  <p className="text-sm text-slate-600">{e.institution}</p>
                  <p className="mt-0.5 text-xs text-slate-400">
                    {[e.field_of_study, e.year_of_passing, e.grade_or_percentage]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                {canEdit && (
                  <button
                    type="button"
                    className="text-slate-400 hover:text-red-600"
                    onClick={() => deleteEducation.mutate(e.id)}
                    aria-label="Delete education"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <CardHeader
          title="Previous work experience"
          description="Prior companies and roles for employment verification"
          action={
            canEdit ? (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => {
                  setExpForm(emptyExperience);
                  setFormErr("");
                  setExpModal(true);
                }}
              >
                <Plus className="mr-1 h-4 w-4" />
                Add
              </Button>
            ) : undefined
          }
        />
        {!data.work_experiences.length ? (
          <p className="text-sm text-slate-500">No previous employment recorded.</p>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
            {data.work_experiences.map((e) => (
              <li key={e.id} className="flex items-start justify-between gap-3 px-4 py-3">
                <div>
                  <p className="font-medium text-slate-900">
                    {e.designation} · {e.company_name}
                  </p>
                  <p className="text-sm text-slate-500">
                    {e.start_date ?? "—"} → {e.is_current ? "Present" : e.end_date ?? "—"}
                    {e.location ? ` · ${e.location}` : ""}
                  </p>
                  {e.reason_for_leaving && (
                    <p className="mt-1 text-xs text-slate-400">Left: {e.reason_for_leaving}</p>
                  )}
                  {e.responsibilities && (
                    <p className="mt-1 text-sm text-slate-600">{e.responsibilities}</p>
                  )}
                </div>
                {canEdit && (
                  <button
                    type="button"
                    className="text-slate-400 hover:text-red-600"
                    onClick={() => deleteExperience.mutate(e.id)}
                    aria-label="Delete experience"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {mode === "hr" && (
        <Card>
          <CardHeader title="Uploaded documents" description="Identity and other files for verification" />
          {!data.documents.length ? (
            <p className="text-sm text-slate-500">No documents uploaded.</p>
          ) : (
            <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
              {data.documents.map((doc) => (
                <li
                  key={doc.id}
                  className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="font-medium text-slate-900">{doc.title}</p>
                    <p className="text-xs text-slate-500">
                      {doc.document_type.replace(/_/g, " ")} · {doc.file_name}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button type="button" size="sm" variant="secondary" onClick={() => openDoc(doc)}>
                      <Eye className="mr-1 h-3.5 w-3.5" />
                      View
                    </Button>
                    <Button type="button" size="sm" variant="secondary" onClick={() => downloadDoc(doc)}>
                      <Download className="mr-1 h-3.5 w-3.5" />
                      Download
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      <Modal open={eduModal} onClose={() => setEduModal(false)} title="Add academic record">
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            addEducation.mutate();
          }}
        >
          <Input
            label="Degree / qualification"
            required
            value={eduForm.degree}
            onChange={(e) => setEduForm((f) => ({ ...f, degree: e.target.value }))}
            placeholder="e.g. B.Tech, MBA"
          />
          <Input
            label="Institution"
            required
            value={eduForm.institution}
            onChange={(e) => setEduForm((f) => ({ ...f, institution: e.target.value }))}
          />
          <Input
            label="Field of study"
            value={eduForm.field_of_study}
            onChange={(e) => setEduForm((f) => ({ ...f, field_of_study: e.target.value }))}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Year of passing"
              type="number"
              value={eduForm.year_of_passing}
              onChange={(e) => setEduForm((f) => ({ ...f, year_of_passing: e.target.value }))}
            />
            <Input
              label="Grade / %"
              value={eduForm.grade_or_percentage}
              onChange={(e) => setEduForm((f) => ({ ...f, grade_or_percentage: e.target.value }))}
            />
          </div>
          {formErr && <p className="text-sm text-red-600">{formErr}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setEduModal(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={addEducation.isPending}>
              {addEducation.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal open={expModal} onClose={() => setExpModal(false)} title="Add work experience">
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            addExperience.mutate();
          }}
        >
          <Input
            label="Company"
            required
            value={expForm.company_name}
            onChange={(e) => setExpForm((f) => ({ ...f, company_name: e.target.value }))}
          />
          <Input
            label="Designation"
            required
            value={expForm.designation}
            onChange={(e) => setExpForm((f) => ({ ...f, designation: e.target.value }))}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Start date"
              type="date"
              value={expForm.start_date}
              onChange={(e) => setExpForm((f) => ({ ...f, start_date: e.target.value }))}
            />
            <Input
              label="End date"
              type="date"
              disabled={expForm.is_current}
              value={expForm.end_date}
              onChange={(e) => setExpForm((f) => ({ ...f, end_date: e.target.value }))}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={expForm.is_current}
              onChange={(e) => setExpForm((f) => ({ ...f, is_current: e.target.checked }))}
            />
            This is my current role
          </label>
          <Input
            label="Location"
            value={expForm.location}
            onChange={(e) => setExpForm((f) => ({ ...f, location: e.target.value }))}
          />
          <Input
            label="Last drawn salary"
            value={expForm.last_drawn_salary}
            onChange={(e) => setExpForm((f) => ({ ...f, last_drawn_salary: e.target.value }))}
          />
          <Input
            label="Reason for leaving"
            value={expForm.reason_for_leaving}
            onChange={(e) => setExpForm((f) => ({ ...f, reason_for_leaving: e.target.value }))}
          />
          <Field label="Responsibilities">
            <textarea
              className={textareaClass()}
              rows={3}
              value={expForm.responsibilities}
              onChange={(e) => setExpForm((f) => ({ ...f, responsibilities: e.target.value }))}
            />
          </Field>
          {formErr && <p className="text-sm text-red-600">{formErr}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setExpModal(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={addExperience.isPending}>
              {addExperience.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={!!preview}
        onClose={() => {
          if (preview?.url) URL.revokeObjectURL(preview.url);
          setPreview(null);
        }}
        title={preview?.doc.title ?? "Document"}
        wide
      >
        {preview && (
          <div className="max-h-[70vh] overflow-auto">
            {(preview.doc.content_type || "").includes("pdf") || /\.pdf$/i.test(preview.doc.file_name) ? (
              <iframe title="preview" src={preview.url} className="h-[65vh] w-full rounded border" />
            ) : (
              <img src={preview.url} alt={preview.doc.file_name} className="mx-auto max-h-[65vh] object-contain" />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
