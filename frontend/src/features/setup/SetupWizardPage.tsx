import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useAuthStore } from "@/store/auth";

interface SetupProgress {
  is_setup_complete: boolean;
  steps: {
    company_profile: boolean;
    working_days: boolean;
  };
  company_profile: {
    timezone: string;
    currency: string;
    country: string;
    fiscal_year_start_month: number;
  } | null;
  working_days: {
    monday: boolean;
    tuesday: boolean;
    wednesday: boolean;
    thursday: boolean;
    friday: boolean;
    saturday: boolean;
    sunday: boolean;
  } | null;
}

const STEPS = [
  { title: "Company Profile", description: "Timezone, currency, and fiscal year" },
  { title: "Working Days", description: "Define your standard work week" },
  { title: "Review & Finish", description: "Confirm and go live" },
];

const DAY_LABELS = [
  { key: "monday", label: "Monday" },
  { key: "tuesday", label: "Tuesday" },
  { key: "wednesday", label: "Wednesday" },
  { key: "thursday", label: "Thursday" },
  { key: "friday", label: "Friday" },
  { key: "saturday", label: "Saturday" },
  { key: "sunday", label: "Sunday" },
] as const;

const DEFAULT_PROFILE = {
  timezone: "Asia/Kolkata",
  currency: "INR",
  country: "India",
  fiscal_year_start_month: 4,
};

const DEFAULT_WORKING_DAYS = {
  monday: true,
  tuesday: true,
  wednesday: true,
  thursday: true,
  friday: true,
  saturday: false,
  sunday: false,
};

export function SetupWizardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState(DEFAULT_PROFILE);
  const [workingDays, setWorkingDays] = useState(DEFAULT_WORKING_DAYS);
  const [hydrated, setHydrated] = useState(false);

  const { data: progress, isLoading } = useQuery({
    queryKey: ["setup-progress"],
    queryFn: () =>
      apiRequest<SetupProgress>("/api/v1/setup/progress", { token: accessToken }),
  });

  useEffect(() => {
    if (!progress || hydrated) return;
    if (progress.company_profile) setProfile(progress.company_profile);
    if (progress.working_days) setWorkingDays(progress.working_days);
    if (progress.steps.company_profile && !progress.steps.working_days) setStep(1);
    if (progress.steps.company_profile && progress.steps.working_days) setStep(2);
    setHydrated(true);
  }, [progress, hydrated]);

  const saveProfileMutation = useMutation({
    mutationFn: () =>
      apiRequest("/api/v1/setup/profile", {
        method: "PUT",
        token: accessToken,
        body: JSON.stringify(profile),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["setup-progress"] });
      setStep(1);
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const saveWorkingDaysMutation = useMutation({
    mutationFn: () =>
      apiRequest("/api/v1/setup/working-days", {
        method: "PUT",
        token: accessToken,
        body: JSON.stringify(workingDays),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["setup-progress"] });
      setStep(2);
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const completeMutation = useMutation({
    mutationFn: () =>
      apiRequest<{ is_setup_complete: boolean }>("/api/v1/setup/complete", {
        method: "POST",
        token: accessToken,
      }),
    onSuccess: async () => {
      const me = await apiRequest<{ is_setup_complete: boolean }>("/api/v1/auth/me", {
        token: accessToken,
      });
      if (user) setUser({ ...user, ...me });
      navigate("/app/dashboard", { replace: true });
    },
    onError: (err: Error) => setError(err.message),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-slate-500">Loading setup wizard...</p>
      </div>
    );
  }

  if (progress?.is_setup_complete) {
    return <Navigate to="/app/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-brand-50 px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-900">Welcome to EmployeeMint</h1>
          <p className="mt-2 text-slate-500">
            Complete these quick steps to set up {user?.tenant_slug || "your organization"}
          </p>
        </div>

        <div className="mb-8 flex justify-center gap-2">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-2 w-16 rounded-full ${i <= step ? "bg-brand-600" : "bg-slate-200"}`}
            />
          ))}
        </div>

        <Card>
          <CardHeader title={STEPS[step].title} description={STEPS[step].description} />

          {step === 0 && (
            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                saveProfileMutation.mutate();
              }}
            >
              <Input
                label="Country"
                value={profile.country}
                onChange={(e) => setProfile((p) => ({ ...p, country: e.target.value }))}
                required
              />
              <Input
                label="Timezone"
                placeholder="Asia/Kolkata"
                value={profile.timezone}
                onChange={(e) => setProfile((p) => ({ ...p, timezone: e.target.value }))}
                required
              />
              <Input
                label="Currency (3-letter code)"
                placeholder="INR"
                maxLength={3}
                value={profile.currency}
                onChange={(e) =>
                  setProfile((p) => ({ ...p, currency: e.target.value.toUpperCase() }))
                }
                required
              />
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-700">
                  Fiscal year starts in
                </label>
                <select
                  value={profile.fiscal_year_start_month}
                  onChange={(e) =>
                    setProfile((p) => ({
                      ...p,
                      fiscal_year_start_month: Number(e.target.value),
                    }))
                  }
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  {[
                    "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December",
                  ].map((month, i) => (
                    <option key={month} value={i + 1}>{month}</option>
                  ))}
                </select>
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <Button type="submit" disabled={saveProfileMutation.isPending}>
                {saveProfileMutation.isPending ? "Saving..." : "Continue"}
              </Button>
            </form>
          )}

          {step === 1 && (
            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                saveWorkingDaysMutation.mutate();
              }}
            >
              <p className="text-sm text-slate-600">Select your standard working days:</p>
              <div className="grid grid-cols-2 gap-3">
                {DAY_LABELS.map(({ key, label }) => (
                  <label
                    key={key}
                    className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={workingDays[key]}
                      onChange={(e) =>
                        setWorkingDays((d) => ({ ...d, [key]: e.target.checked }))
                      }
                      className="rounded border-slate-300"
                    />
                    {label}
                  </label>
                ))}
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex gap-3">
                <Button type="button" variant="secondary" onClick={() => setStep(0)}>
                  Back
                </Button>
                <Button type="submit" disabled={saveWorkingDaysMutation.isPending}>
                  {saveWorkingDaysMutation.isPending ? "Saving..." : "Continue"}
                </Button>
              </div>
            </form>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
                <p className="font-medium text-slate-900">Setup checklist</p>
                <ul className="mt-3 space-y-2">
                  <li className="flex items-center gap-2">
                    <span className={progress?.steps.company_profile ? "text-green-600" : "text-red-500"}>
                      {progress?.steps.company_profile ? "✓" : "○"}
                    </span>
                    Company profile configured
                  </li>
                  <li className="flex items-center gap-2">
                    <span className={progress?.steps.working_days ? "text-green-600" : "text-red-500"}>
                      {progress?.steps.working_days ? "✓" : "○"}
                    </span>
                    Working days configured
                  </li>
                </ul>
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex gap-3">
                <Button type="button" variant="secondary" onClick={() => setStep(1)}>
                  Back
                </Button>
                <Button
                  onClick={() => {
                    setError("");
                    completeMutation.mutate();
                  }}
                  disabled={
                    completeMutation.isPending ||
                    !progress?.steps.company_profile ||
                    !progress?.steps.working_days
                  }
                >
                  {completeMutation.isPending ? "Finishing..." : "Complete Setup"}
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
