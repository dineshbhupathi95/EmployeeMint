import { useQuery } from "@tanstack/react-query";
import { Building2, Users } from "lucide-react";
import { apiRequest } from "@/api/client";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/Modal";
import { useAuthStore } from "@/store/auth";

interface OrgNode {
  id: string;
  name: string;
  employee_code: string;
  designation: string | null;
  department: string | null;
  children: OrgNode[];
}

function initials(name: string) {
  return name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
}

function OrgChartNode({ node }: { node: OrgNode }) {
  const hasChildren = node.children.length > 0;

  return (
    <li className="flex flex-col items-center">
      <div className="group relative z-10 w-52 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-sm font-bold text-white">
            {initials(node.name)}
          </div>
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-900">{node.name}</p>
            <p className="truncate text-xs text-slate-500">{node.designation ?? "Team Member"}</p>
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-xs text-slate-400">
          <span className="font-mono">{node.employee_code}</span>
          {node.department && (
            <span className="flex items-center gap-1 truncate">
              <Building2 className="h-3 w-3" />
              {node.department}
            </span>
          )}
        </div>
      </div>

      {hasChildren && (
        <>
          <div className="h-6 w-px bg-slate-300" />
          <div className="relative flex justify-center">
            <div className="absolute top-0 h-px bg-slate-300" style={{ left: "12.5%", right: "12.5%" }} />
            <ul className="flex gap-8 pt-0">
              {node.children.map((child) => (
                <div key={child.id} className="flex flex-col items-center">
                  <div className="h-6 w-px bg-slate-300" />
                  <OrgChartNode node={child} />
                </div>
              ))}
            </ul>
          </div>
        </>
      )}
    </li>
  );
}

function countNodes(nodes: OrgNode[]): number {
  return nodes.reduce((sum, n) => sum + 1 + countNodes(n.children), 0);
}

export function OrganizationPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const { data: tree, isLoading } = useQuery({
    queryKey: ["org-tree"],
    queryFn: () => apiRequest<OrgNode[]>("/api/v1/organization/tree", { token: accessToken }),
  });

  const total = tree ? countNodes(tree) : 0;
  const roots = tree?.length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Organization"
        description="Interactive reporting hierarchy and team structure"
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="border-brand-100 bg-gradient-to-br from-brand-50 to-white">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-brand-100 p-2">
              <Users className="h-5 w-5 text-brand-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{total}</p>
              <p className="text-sm text-slate-500">Total in chart</p>
            </div>
          </div>
        </Card>
        <Card>
          <p className="text-2xl font-bold text-slate-900">{roots}</p>
          <p className="text-sm text-slate-500">Top-level leaders</p>
        </Card>
        <Card>
          <p className="text-2xl font-bold text-slate-900">{tree ? Math.max(0, total - roots) : 0}</p>
          <p className="text-sm text-slate-500">Direct reports</p>
        </Card>
      </div>

      <Card className="overflow-x-auto">
        {isLoading ? (
          <p className="py-12 text-center text-slate-500">Loading org chart...</p>
        ) : tree?.length ? (
          <div className="min-w-max px-8 py-10">
            <ul className="flex justify-center gap-12">
              {tree.map((node) => (
                <OrgChartNode key={node.id} node={node} />
              ))}
            </ul>
          </div>
        ) : (
          <p className="py-12 text-center text-slate-500">No employees found. Assign managers in Employees to build the chart.</p>
        )}
      </Card>
    </div>
  );
}
