import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, FileSpreadsheet, TrendingUp, Users, Calendar, CheckCircle } from "lucide-react";
import { apiDownload, apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/Modal";
import { useAuthStore } from "@/store/auth";

interface ReportSummary {
  headcount: number;
  pending_leave_requests: number;
  present_today: number;
  approved_leave_requests: number;
}

export function ReportsPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const { data, isLoading } = useQuery({
    queryKey: ["reports-summary"],
    queryFn: () => apiRequest<ReportSummary>("/api/v1/reports/summary", { token: accessToken }),
  });

  const exportMutation = useMutation({
    mutationFn: async () => {
      const blob = await apiDownload("/api/v1/reports/export", accessToken);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `employeemint-report-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const cards = [
    { label: "Active Headcount", value: data?.headcount, desc: "Currently active employees", icon: Users, color: "from-blue-500 to-blue-600" },
    { label: "Present Today", value: data?.present_today, desc: "Checked in today", icon: CheckCircle, color: "from-emerald-500 to-emerald-600" },
    { label: "Pending Leave", value: data?.pending_leave_requests, desc: "Awaiting approval", icon: Calendar, color: "from-amber-500 to-amber-600" },
    { label: "Approved Leave", value: data?.approved_leave_requests, desc: "All time approved", icon: TrendingUp, color: "from-violet-500 to-violet-600" },
  ];

  return (
    <div>
      <PageHeader
        title="Reports"
        description="HR analytics and workforce insights"
        action={
          <Button onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
            <Download className="mr-2 h-4 w-4" />
            {exportMutation.isPending ? "Exporting..." : "Download Excel"}
          </Button>
        }
      />

      {isLoading ? (
        <p className="text-slate-500">Loading reports...</p>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((c) => {
            const Icon = c.icon;
            return (
              <Card key={c.label} className="overflow-hidden p-0">
                <div className={`bg-gradient-to-r ${c.color} px-5 py-3`}>
                  <Icon className="h-5 w-5 text-white/90" />
                </div>
                <div className="p-5">
                  <p className="text-sm font-medium text-slate-500">{c.label}</p>
                  <p className="mt-1 text-3xl font-bold text-slate-900">{c.value ?? "—"}</p>
                  <p className="mt-1 text-xs text-slate-400">{c.desc}</p>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <Card className="mt-6">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-green-50 p-3">
            <FileSpreadsheet className="h-6 w-6 text-green-600" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-slate-900">Export to Excel</h3>
            <p className="mt-1 text-sm text-slate-500">
              Download a spreadsheet with summary metrics, employee list, leave requests, and today&apos;s attendance.
              Opens directly in Microsoft Excel or Google Sheets.
            </p>
            <Button className="mt-4" variant="secondary" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
              <Download className="mr-2 h-4 w-4" />
              Download Report (.csv)
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
