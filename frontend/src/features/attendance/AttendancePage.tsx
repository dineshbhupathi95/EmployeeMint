import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { useAuthStore } from "@/store/auth";

interface AttendanceRecord {
  id: string; date: string; check_in: string | null; check_out: string | null; mode: string; status: string;
}

export function AttendancePage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [mode, setMode] = useState("in_office");
  const [error, setError] = useState("");
  const [viewDate, setViewDate] = useState(new Date());
  const [showRegularize, setShowRegularize] = useState(false);
  const [regForm, setRegForm] = useState({ date: "", mode: "in_office", check_in_time: "09:00", check_out_time: "18:00", reason: "" });

  const year = viewDate.getFullYear();
  const month = viewDate.getMonth() + 1;
  const todayStr = new Date().toISOString().slice(0, 10);

  const { data: records } = useQuery({
    queryKey: ["attendance", year, month],
    queryFn: () => apiRequest<AttendanceRecord[]>(`/api/v1/attendance/my?year=${year}&month=${month}`, { token: accessToken }),
  });

  const recordMap = useMemo(() => {
    const m = new Map<string, AttendanceRecord>();
    records?.forEach((r) => m.set(r.date, r));
    return m;
  }, [records]);

  const calendarDays = useMemo(() => {
    const last = new Date(year, month, 0);
    const days: { date: string; day: number; isToday: boolean; isFuture: boolean }[] = [];
    for (let d = 1; d <= last.getDate(); d++) {
      const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      days.push({ date: dateStr, day: d, isToday: dateStr === todayStr, isFuture: dateStr > todayStr });
    }
    return days;
  }, [year, month, todayStr]);

  const today = recordMap.get(todayStr);
  const isCurrentMonth = viewDate.getFullYear() === new Date().getFullYear() && viewDate.getMonth() === new Date().getMonth();

  const shiftMonth = (delta: number) => {
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + delta, 1));
  };

  const checkInMutation = useMutation({
    mutationFn: () => apiRequest("/api/v1/attendance/check-in", { method: "POST", token: accessToken, body: JSON.stringify({ mode }) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["attendance"] }); setError(""); },
    onError: (err: Error) => setError(err.message),
  });

  const checkOutMutation = useMutation({
    mutationFn: () => apiRequest("/api/v1/attendance/check-out", { method: "POST", token: accessToken }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["attendance"] }); setError(""); },
    onError: (err: Error) => setError(err.message),
  });

  const regularizeMutation = useMutation({
    mutationFn: () => apiRequest("/api/v1/attendance/regularize", { method: "POST", token: accessToken, body: JSON.stringify(regForm) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["attendance"] }); setShowRegularize(false); setError(""); },
    onError: (err: Error) => setError(err.message),
  });

  const monthLabel = viewDate.toLocaleString("default", { month: "long", year: "numeric" });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attendance"
        description="Check in/out, view past & future months, regularize missed days"
        action={<Button variant="secondary" onClick={() => setShowRegularize(true)}>Regularize Past Day</Button>}
      />

      {isCurrentMonth && (
        <Card>
          <CardHeader title="Today's Attendance" description={new Date().toDateString()} />
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Work Mode</label>
              <select className="rounded-lg border border-slate-200 px-3 py-2 text-sm" value={mode}
                onChange={(e) => setMode(e.target.value)} disabled={!!today?.check_in}>
                <option value="in_office">In Office</option>
                <option value="remote">Remote</option>
                <option value="wfh">Work From Home</option>
              </select>
            </div>
            <Button onClick={() => checkInMutation.mutate()} disabled={!!today?.check_in || checkInMutation.isPending}>
              {today?.check_in ? "Checked In" : "Check In"}
            </Button>
            <Button variant="secondary" onClick={() => checkOutMutation.mutate()}
              disabled={!today?.check_in || !!today?.check_out || checkOutMutation.isPending}>
              {today?.check_out ? "Checked Out" : "Check Out"}
            </Button>
          </div>
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        </Card>
      )}

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <Button variant="secondary" size="sm" onClick={() => shiftMonth(-1)}>← Prev</Button>
          <h3 className="font-semibold text-slate-900">{monthLabel}</h3>
          <Button variant="secondary" size="sm" onClick={() => shiftMonth(1)}>Next →</Button>
        </div>
        <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-slate-500">
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => <div key={d} className="py-2">{d}</div>)}
        </div>
        <div className="grid grid-cols-7 gap-1">
          {Array.from({ length: new Date(year, month - 1, 1).getDay() }).map((_, i) => <div key={`pad-${i}`} />)}
          {calendarDays.map(({ date, day, isToday, isFuture }) => {
            const rec = recordMap.get(date);
            const status = isFuture ? "future" : rec?.check_in ? (rec.check_out ? "complete" : "partial") : "absent";
            return (
              <div key={date}
                className={`rounded-lg border p-2 text-center text-xs ${
                  isToday ? "border-brand-500 bg-brand-50" :
                  status === "complete" ? "border-green-200 bg-green-50" :
                  status === "partial" ? "border-yellow-200 bg-yellow-50" :
                  status === "future" ? "border-slate-100 bg-slate-50 text-slate-400" :
                  "border-red-100 bg-red-50"
                }`}>
                <div className="font-medium">{day}</div>
                <div className="mt-1 capitalize">{isFuture ? "—" : rec ? rec.mode.replace("_", " ") : "Absent"}</div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <CardHeader title={`Records — ${monthLabel}`} />
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-slate-500">
              <th className="pb-2">Date</th><th className="pb-2">Mode</th><th className="pb-2">In</th><th className="pb-2">Out</th><th className="pb-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {records?.map((r) => (
              <tr key={r.id} className="border-b border-slate-100">
                <td className="py-2">{r.date}</td>
                <td className="py-2 capitalize">{r.mode.replace("_", " ")}</td>
                <td className="py-2">{r.check_in ? new Date(r.check_in).toLocaleTimeString() : "—"}</td>
                <td className="py-2">{r.check_out ? new Date(r.check_out).toLocaleTimeString() : "—"}</td>
                <td className="py-2 capitalize">{r.status}</td>
              </tr>
            ))}
            {!records?.length && (
              <tr><td colSpan={5} className="py-4 text-center text-slate-500">No records for this month</td></tr>
            )}
          </tbody>
        </table>
      </Card>

      <Modal open={showRegularize} onClose={() => setShowRegularize(false)} title="Regularize Attendance">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); regularizeMutation.mutate(); }}>
          <Input label="Date" type="date" required max={todayStr} value={regForm.date}
            onChange={(e) => setRegForm((f) => ({ ...f, date: e.target.value }))} />
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Mode</label>
            <select className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" value={regForm.mode}
              onChange={(e) => setRegForm((f) => ({ ...f, mode: e.target.value }))}>
              <option value="in_office">In Office</option>
              <option value="remote">Remote</option>
              <option value="wfh">Work From Home</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Check In" type="time" value={regForm.check_in_time}
              onChange={(e) => setRegForm((f) => ({ ...f, check_in_time: e.target.value }))} />
            <Input label="Check Out" type="time" value={regForm.check_out_time}
              onChange={(e) => setRegForm((f) => ({ ...f, check_out_time: e.target.value }))} />
          </div>
          <Input label="Reason" required value={regForm.reason}
            onChange={(e) => setRegForm((f) => ({ ...f, reason: e.target.value }))} />
          <p className="text-xs text-slate-500">Regularization requests are sent to your manager for approval.</p>
          <Button type="submit" disabled={regularizeMutation.isPending}>Submit Regularization</Button>
        </form>
      </Modal>
    </div>
  );
}
