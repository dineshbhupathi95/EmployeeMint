import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import { useQuery } from "@tanstack/react-query";
import { Building2, ChevronDown, ChevronRight, LocateFixed, Users } from "lucide-react";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

interface OrgNode {
  id: string;
  name: string;
  employee_code: string;
  designation: string | null;
  department: string | null;
  reports_to?: string | null;
  children: OrgNode[];
}

function initials(name: string) {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function countNodes(nodes: OrgNode[]): number {
  return nodes.reduce((sum, n) => sum + 1 + countNodes(n.children), 0);
}

/** Ancestors of target (not including target), root → parent order. */
function findAncestorPath(nodes: OrgNode[], targetId: string): string[] | null {
  for (const node of nodes) {
    if (node.id === targetId) return [];
    const childPath = findAncestorPath(node.children, targetId);
    if (childPath) return [node.id, ...childPath];
  }
  return null;
}

function OrgChartNode({
  node,
  currentEmployeeId,
  collapsed,
  onToggle,
  meRef,
}: {
  node: OrgNode;
  currentEmployeeId: string | undefined;
  collapsed: Set<string>;
  onToggle: (id: string) => void;
  meRef: RefObject<HTMLDivElement>;
}) {
  const hasChildren = node.children.length > 0;
  const isExpanded = hasChildren && !collapsed.has(node.id);
  const isMe = currentEmployeeId === node.id;

  return (
    <li className="flex flex-col items-center">
      <div
        ref={isMe ? meRef : undefined}
        className={cn(
          "group relative z-10 w-52 rounded-xl border bg-white p-4 shadow-sm transition-shadow hover:shadow-md",
          isMe
            ? "border-brand-500 ring-2 ring-brand-200 ring-offset-2"
            : "border-slate-200",
        )}
      >
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white",
              isMe
                ? "bg-gradient-to-br from-brand-600 to-brand-800"
                : "bg-gradient-to-br from-brand-500 to-brand-700",
            )}
          >
            {initials(node.name)}
          </div>
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-900">
              {node.name}
              {isMe && (
                <span className="ml-1.5 text-xs font-medium text-brand-600">(You)</span>
              )}
            </p>
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
        {hasChildren && (
          <button
            type="button"
            onClick={() => onToggle(node.id)}
            className="absolute -bottom-3 left-1/2 z-20 flex h-6 w-6 -translate-x-1/2 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 shadow-sm hover:bg-slate-50"
            aria-label={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        )}
      </div>

      {hasChildren && isExpanded && (
        <>
          <div className="h-6 w-px bg-slate-300" />
          <div className="relative flex justify-center">
            <div
              className="absolute top-0 h-px bg-slate-300"
              style={{ left: "12.5%", right: "12.5%" }}
            />
            <ul className="flex gap-8 pt-0">
              {node.children.map((child) => (
                <div key={child.id} className="flex flex-col items-center">
                  <div className="h-6 w-px bg-slate-300" />
                  <OrgChartNode
                    node={child}
                    currentEmployeeId={currentEmployeeId}
                    collapsed={collapsed}
                    onToggle={onToggle}
                    meRef={meRef}
                  />
                </div>
              ))}
            </ul>
          </div>
        </>
      )}
    </li>
  );
}

export function OrganizationPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const currentEmployeeId = useAuthStore((s) => s.user?.employee_id ?? undefined);
  const meRef = useRef<HTMLDivElement>(null!);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [initialized, setInitialized] = useState(false);

  const { data: tree, isLoading } = useQuery({
    queryKey: ["org-tree"],
    queryFn: () => apiRequest<OrgNode[]>("/api/v1/organization/tree", { token: accessToken }),
  });

  const total = tree ? countNodes(tree) : 0;
  const roots = tree?.length ?? 0;

  const nodesWithChildren = useMemo(() => {
    if (!tree) return new Set<string>();
    const ids = new Set<string>();
    const walk = (nodes: OrgNode[]) => {
      for (const n of nodes) {
        if (n.children.length > 0) ids.add(n.id);
        walk(n.children);
      }
    };
    walk(tree);
    return ids;
  }, [tree]);

  const collapsedExceptPathToMe = () => {
    if (!tree) return new Set<string>();
    if (!currentEmployeeId) return new Set<string>();
    const path = findAncestorPath(tree, currentEmployeeId);
    if (path === null) return new Set(nodesWithChildren);
    const pathSet = new Set(path);
    const next = new Set<string>();
    for (const id of nodesWithChildren) {
      if (!pathSet.has(id)) next.add(id);
    }
    return next;
  };

  // Default: expand path to logged-in user; collapse other branches
  useEffect(() => {
    if (!tree?.length || initialized) return;
    setCollapsed(collapsedExceptPathToMe());
    setInitialized(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once when tree loads
  }, [tree, currentEmployeeId, initialized, nodesWithChildren]);

  useEffect(() => {
    if (!initialized || !currentEmployeeId) return;
    const t = window.setTimeout(() => {
      meRef.current?.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
    }, 150);
    return () => window.clearTimeout(t);
  }, [initialized, currentEmployeeId]);

  const toggle = (id: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const expandAll = () => setCollapsed(new Set());
  const collapseAll = () => setCollapsed(new Set(nodesWithChildren));

  const focusMe = () => {
    setCollapsed(collapsedExceptPathToMe());
    window.setTimeout(() => {
      meRef.current?.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
    }, 100);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Organization"
        description="Full reporting hierarchy — you are highlighted in the chart"
        action={
          <div className="flex flex-wrap gap-2">
            {currentEmployeeId && (
              <Button type="button" variant="secondary" size="sm" onClick={focusMe}>
                <LocateFixed className="mr-1.5 h-4 w-4" />
                Find me
              </Button>
            )}
            <Button type="button" variant="secondary" size="sm" onClick={expandAll}>
              Expand all
            </Button>
            <Button type="button" variant="secondary" size="sm" onClick={collapseAll}>
              Collapse all
            </Button>
          </div>
        }
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
          <p className="text-sm text-slate-500">Reports under leaders</p>
        </Card>
      </div>

      <Card className="overflow-x-auto">
        {isLoading ? (
          <p className="py-12 text-center text-slate-500">Loading org chart...</p>
        ) : tree?.length ? (
          <div className="min-w-max px-8 py-10">
            <ul className="flex justify-center gap-12">
              {tree.map((node) => (
                <OrgChartNode
                  key={node.id}
                  node={node}
                  currentEmployeeId={currentEmployeeId}
                  collapsed={collapsed}
                  onToggle={toggle}
                  meRef={meRef}
                />
              ))}
            </ul>
          </div>
        ) : (
          <p className="py-12 text-center text-slate-500">
            No employees found. Assign managers in Employees to build the chart.
          </p>
        )}
      </Card>
    </div>
  );
}
