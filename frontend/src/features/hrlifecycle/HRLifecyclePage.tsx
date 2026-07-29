import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { FileText, LogOut, UserPlus } from "lucide-react";
import { apiRequest } from "@/api/client";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/Modal";
import { useAnyPermission, useModuleVisible } from "@/hooks/usePermission";
import { useAuthStore } from "@/store/auth";

const MODULES = [
  {
    title: "Onboarding",
    description: "Start checklists for new hires — tasks are created when you assign an employee",
    path: "/app/onboarding",
    icon: UserPlus,
    module: "onboarding",
    countKey: "onboarding" as const,
    cta: "Start onboarding →",
  },
  {
    title: "Offer Letters",
    description: "Draft → Generate PDF → Release offer to candidate",
    path: "/app/offer-letters",
    icon: FileText,
    module: "offer_letters",
    countKey: "offers" as const,
    cta: "Manage offers →",
  },
  {
    title: "Offboarding",
    description: "Exit requests and last working day tracking",
    path: "/app/offboarding",
    icon: LogOut,
    module: "offboarding",
    countKey: "offboarding" as const,
    cta: "View exits →",
  },
];

function LifecycleCard({
  mod,
  count,
}: {
  mod: (typeof MODULES)[number];
  count: number;
}) {
  const Icon = mod.icon;
  return (
    <Link to={mod.path}>
      <Card className="h-full transition-shadow hover:shadow-md">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <Icon className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-slate-900">{mod.title}</p>
            <p className="mt-1 text-sm text-slate-500">{mod.description}</p>
            <p className="mt-3 text-2xl font-bold text-brand-700">{count}</p>
            <p className="text-xs text-slate-400">records</p>
            <p className="mt-2 text-sm font-medium text-brand-600">{mod.cta}</p>
          </div>
        </div>
      </Card>
    </Link>
  );
}

function LifecycleModuleCard({
  mod,
  count,
}: {
  mod: (typeof MODULES)[number];
  count: number;
}) {
  const visible = useModuleVisible(mod.module);
  if (!visible) return null;
  return <LifecycleCard mod={mod} count={count} />;
}

export function HRLifecyclePage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const canOnboarding = useAnyPermission(["onboarding.manage"]);
  const canOffboarding = useAnyPermission(["offboarding.manage"]);
  const canOffers = useAnyPermission(["offer_letter.generate"]);

  const { data: onboarding } = useQuery({
    queryKey: ["onboarding-tasks"],
    queryFn: () => apiRequest<{ id: string }[]>("/api/v1/onboarding/tasks", { token: accessToken }),
    enabled: canOnboarding,
  });

  const { data: offboarding } = useQuery({
    queryKey: ["exit-requests"],
    queryFn: () => apiRequest<{ id: string }[]>("/api/v1/offboarding/requests", { token: accessToken }),
    enabled: canOffboarding,
  });

  const { data: offers } = useQuery({
    queryKey: ["offer-letters"],
    queryFn: () => apiRequest<{ id: string }[]>("/api/v1/offer-letters", { token: accessToken }),
    enabled: canOffers,
  });

  const counts = {
    onboarding: onboarding?.length ?? 0,
    offboarding: offboarding?.length ?? 0,
    offers: offers?.length ?? 0,
  };

  const showOnboarding = useModuleVisible("onboarding");
  const showOffboarding = useModuleVisible("offboarding");
  const showOffers = useModuleVisible("offer_letters");
  const anyVisible = showOnboarding || showOffboarding || showOffers;

  return (
    <div className="space-y-6">
      <PageHeader
        title="HR Lifecycle"
        description="Hire-to-retire: onboarding new employees, issuing offer letters, and managing exits"
      />

      <Card className="bg-brand-50 border-brand-100">
        <p className="text-sm text-brand-900">
          <strong>Quick guide:</strong> Onboarding starts empty — pick an employee on the Onboarding page and click
          &quot;Start Standard Checklist&quot;. For offers, create a draft, generate the PDF, then release it to the candidate.
        </p>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <LifecycleModuleCard mod={MODULES[0]} count={counts.onboarding} />
        <LifecycleModuleCard mod={MODULES[1]} count={counts.offers} />
        <LifecycleModuleCard mod={MODULES[2]} count={counts.offboarding} />
        {!anyVisible && (
          <Card className="sm:col-span-2 lg:col-span-3">
            <p className="text-sm text-slate-500">You do not have access to HR lifecycle modules.</p>
          </Card>
        )}
      </div>
    </div>
  );
}
