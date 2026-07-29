import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest } from "@/api/client";
import { PlatformLayout } from "@/features/platform/PlatformLayout";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useAuthStore } from "@/store/auth";

export function CreateTenantPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const [form, setForm] = useState({
    name: "",
    slug: "",
    admin_email: "",
    admin_password: "",
    admin_first_name: "",
    admin_last_name: "",
  });
  const [error, setError] = useState("");

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest("/api/v1/platform/tenants", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ ...form, plan: "starter", max_employees: 100 }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-tenants"] });
      navigate("/platform/tenants");
    },
    onError: (err: Error) => setError(err.message),
  });

  const update = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  return (
    <PlatformLayout>
      <div className="mx-auto max-w-2xl">
        <Card>
          <CardHeader
            title="Create Tenant"
            description="Provision a new customer organization"
          />
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              setError("");
              createMutation.mutate();
            }}
          >
            <Input label="Company name" value={form.name} onChange={(e) => update("name", e.target.value)} required />
            <Input label="Slug" placeholder="acme" value={form.slug} onChange={(e) => update("slug", e.target.value)} required />
            <div className="grid grid-cols-2 gap-4">
              <Input label="Admin first name" value={form.admin_first_name} onChange={(e) => update("admin_first_name", e.target.value)} required />
              <Input label="Admin last name" value={form.admin_last_name} onChange={(e) => update("admin_last_name", e.target.value)} required />
            </div>
            <Input label="Admin email" type="email" value={form.admin_email} onChange={(e) => update("admin_email", e.target.value)} required />
            <Input label="Admin password" type="password" value={form.admin_password} onChange={(e) => update("admin_password", e.target.value)} required />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex gap-3">
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create Tenant"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate("/platform/tenants")}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </PlatformLayout>
  );
}
