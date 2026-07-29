import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, PlayCircle, Plus } from "lucide-react";
import { useState } from "react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal, PageHeader } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface OnboardingTask {
  id: string;
  employee_id: string;
  employee_name: string;
  employee_code: string;
  title: string;
  description: string | null;
  status: string;
  due_date: string | null;
}

interface Employee {
  id: string;
  first_name: string;
  last_name: string;
  employee_code: string;
}

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  in_progress: "bg-brand-100 text-brand-800",
  completed: "bg-green-100 text-green-800",
};

export function OnboardingPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const [selectedEmployee, setSelectedEmployee] = useState("");
  const [showAddTask, setShowAddTask] = useState(false);
  const [taskForm, setTaskForm] = useState({ title: "", description: "", due_date: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const { data: tasks } = useQuery({
    queryKey: ["onboarding-tasks"],
    queryFn: () => apiRequest<OnboardingTask[]>("/api/v1/onboarding/tasks", { token: accessToken }),
  });

  const { data: employeesData } = useQuery({
    queryKey: ["employees-onboarding"],
    queryFn: () =>
      apiRequest<{ items: Employee[] }>("/api/v1/employees?page_size=100", { token: accessToken }),
  });

  const employees = employeesData?.items ?? [];
  const employeesWithoutTasks = employees.filter(
    (e) => !tasks?.some((t) => t.employee_id === e.id),
  );

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["onboarding-tasks"] });

  const startMutation = useMutation({
    mutationFn: (employeeId: string) =>
      apiRequest<{ message: string }>(`/api/v1/onboarding/start/${employeeId}`, {
        method: "POST",
        token: accessToken,
      }),
    onSuccess: (data) => {
      invalidate();
      setSelectedEmployee("");
      setMessage(data.message);
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const addTaskMutation = useMutation({
    mutationFn: () =>
      apiRequest("/api/v1/onboarding/tasks", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          employee_id: selectedEmployee,
          title: taskForm.title,
          description: taskForm.description || null,
          due_date: taskForm.due_date || null,
        }),
      }),
    onSuccess: () => {
      invalidate();
      setShowAddTask(false);
      setTaskForm({ title: "", description: "", due_date: "" });
      setMessage("Task added.");
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const completeMutation = useMutation({
    mutationFn: (taskId: string) =>
      apiRequest(`/api/v1/onboarding/tasks/${taskId}`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({ status: "completed" }),
      }),
    onSuccess: () => invalidate(),
  });

  const grouped = tasks?.reduce<Record<string, OnboardingTask[]>>((acc, task) => {
    const key = task.employee_id;
    acc[key] = acc[key] ?? [];
    acc[key].push(task);
    return acc;
  }, {}) ?? {};

  const completedCount = tasks?.filter((t) => t.status === "completed").length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Onboarding"
        description={`Track new hire checklists · ${completedCount}/${tasks?.length ?? 0} tasks completed`}
      />

      {message && <p className="rounded-lg bg-green-50 px-4 py-2 text-sm text-green-700">{message}</p>}
      {error && <p className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      <Card>
        <CardHeader
          title="Start Onboarding"
          description="Onboarding is empty until you assign a checklist to a new hire"
        />
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[220px] flex-1">
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Select Employee</label>
            <select
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              value={selectedEmployee}
              onChange={(e) => setSelectedEmployee(e.target.value)}
            >
              <option value="">Choose employee...</option>
              {employeesWithoutTasks.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.first_name} {e.last_name} ({e.employee_code})
                </option>
              ))}
            </select>
          </div>
          <Button
            disabled={!selectedEmployee || startMutation.isPending}
            onClick={() => startMutation.mutate(selectedEmployee)}
          >
            <PlayCircle className="mr-2 h-4 w-4" />
            {startMutation.isPending ? "Starting..." : "Start Standard Checklist"}
          </Button>
          <Button
            variant="secondary"
            disabled={!selectedEmployee}
            onClick={() => setShowAddTask(true)}
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Custom Task
          </Button>
        </div>
        {!tasks?.length && (
          <p className="mt-4 rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-800">
            No onboarding tasks yet. Select an employee above and click <strong>Start Standard Checklist</strong> to
            auto-create 4 tasks (documents, payroll forms, IT setup, HR orientation).
          </p>
        )}
      </Card>

      {Object.entries(grouped).map(([employeeId, employeeTasks]) => {
        const emp = employeeTasks[0];
        const done = employeeTasks.filter((t) => t.status === "completed").length;
        return (
          <Card key={employeeId}>
            <CardHeader
              title={`${emp.employee_name} (${emp.employee_code})`}
              description={`${done}/${employeeTasks.length} tasks completed`}
            />
            <div className="space-y-2">
              {employeeTasks.map((t) => (
                <div
                  key={t.id}
                  className="flex items-start justify-between gap-3 rounded-lg border border-slate-100 px-4 py-3"
                >
                  <div>
                    <p className="font-medium text-slate-900">{t.title}</p>
                    {t.description && <p className="mt-0.5 text-sm text-slate-500">{t.description}</p>}
                    <p className="mt-1 text-xs text-slate-400">Due: {t.due_date ?? "Not set"}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                        STATUS_STYLES[t.status] ?? STATUS_STYLES.pending,
                      )}
                    >
                      {t.status.replace("_", " ")}
                    </span>
                    {t.status !== "completed" && (
                      <button
                        type="button"
                        onClick={() => completeMutation.mutate(t.id)}
                        className="flex items-center gap-1 text-xs text-green-600 hover:underline"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Mark done
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        );
      })}

      <Modal open={showAddTask} onClose={() => setShowAddTask(false)} title="Add Onboarding Task">
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            addTaskMutation.mutate();
          }}
        >
          <Input
            label="Task Title"
            required
            value={taskForm.title}
            onChange={(e) => setTaskForm((f) => ({ ...f, title: e.target.value }))}
          />
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Description</label>
            <textarea
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              rows={3}
              value={taskForm.description}
              onChange={(e) => setTaskForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>
          <Input
            label="Due Date"
            type="date"
            value={taskForm.due_date}
            onChange={(e) => setTaskForm((f) => ({ ...f, due_date: e.target.value }))}
          />
          <Button type="submit" disabled={addTaskMutation.isPending}>
            {addTaskMutation.isPending ? "Saving..." : "Add Task"}
          </Button>
        </form>
      </Modal>
    </div>
  );
}
