import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useAuthStore } from "@/store/auth";

export function OffboardingPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ resignation_date: "", last_working_date: "", reason: "" });

  const { data: requests } = useQuery({
    queryKey: ["exit-requests"],
    queryFn: () => apiRequest<{ id: string; exit_type: string; status: string; last_working_date: string }[]>("/api/v1/offboarding/requests", { token: accessToken }),
  });

  const submitMutation = useMutation({
    mutationFn: () => apiRequest("/api/v1/offboarding/requests", {
      method: "POST", token: accessToken,
      body: JSON.stringify({ exit_type: "resignation", ...form }),
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["exit-requests"] }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Offboarding</h1>
      <Card>
        <CardHeader title="Initiate Resignation" />
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); submitMutation.mutate(); }}>
          <Input label="Resignation Date" type="date" required value={form.resignation_date} onChange={(e) => setForm((f) => ({ ...f, resignation_date: e.target.value }))} />
          <Input label="Last Working Date" type="date" required value={form.last_working_date} onChange={(e) => setForm((f) => ({ ...f, last_working_date: e.target.value }))} />
          <Input label="Reason" value={form.reason} onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))} />
          <Button type="submit">Submit Exit Request</Button>
        </form>
      </Card>
      <Card>
        <CardHeader title="Exit Requests" />
        <table className="w-full text-sm">
          <thead><tr className="border-b text-slate-500"><th className="pb-2">Type</th><th className="pb-2">LWD</th><th className="pb-2">Status</th></tr></thead>
          <tbody>{requests?.map((r) => (
            <tr key={r.id} className="border-b"><td className="py-2 capitalize">{r.exit_type}</td><td className="py-2">{r.last_working_date}</td><td className="py-2 capitalize">{r.status}</td></tr>
          ))}</tbody>
        </table>
      </Card>
    </div>
  );
}
