import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiRequest } from "@/api/client";
import { PlatformLayout } from "@/features/platform/PlatformLayout";
import type { PaginatedTenants } from "@/features/platform/types";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useAuthStore } from "@/store/auth";

export function PlatformTenantsPage() {
  const accessToken = useAuthStore((s) => s.accessToken);

  const { data, isLoading } = useQuery({
    queryKey: ["platform-tenants"],
    queryFn: () =>
      apiRequest<PaginatedTenants>("/api/v1/platform/tenants", {
        token: accessToken,
      }),
  });

  return (
    <PlatformLayout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Tenants</h2>
          <p className="text-slate-500">Manage customer organizations</p>
        </div>
        <Link to="/platform/tenants/new">
          <Button>Create Tenant</Button>
        </Link>
      </div>
      <Card>
        {isLoading ? (
          <p className="text-slate-500">Loading tenants...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="pb-3 font-medium">Name</th>
                  <th className="pb-3 font-medium">Slug</th>
                  <th className="pb-3 font-medium">Plan</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Setup</th>
                  <th className="pb-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((tenant) => (
                  <tr key={tenant.id} className="border-b border-slate-100">
                    <td className="py-3 font-medium">{tenant.name}</td>
                    <td className="py-3 text-slate-600">{tenant.slug}</td>
                    <td className="py-3 capitalize">{tenant.plan}</td>
                    <td className="py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          tenant.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {tenant.is_active ? "Active" : "Suspended"}
                      </span>
                    </td>
                    <td className="py-3">
                      {tenant.is_setup_complete ? "Complete" : "Pending"}
                    </td>
                    <td className="py-3">
                      <Link
                        to={`/platform/tenants/${tenant.id}`}
                        className="text-brand-600 hover:underline"
                      >
                        View & Manage
                      </Link>
                    </td>
                  </tr>
                ))}
                {data?.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      No tenants yet. Create your first tenant to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PlatformLayout>
  );
}
