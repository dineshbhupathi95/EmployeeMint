import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiDownload, apiRequest } from "@/api/client";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

type Size = "sm" | "md" | "lg";

const SIZE: Record<Size, string> = {
  sm: "h-7 w-7",
  md: "h-9 w-9",
  lg: "h-11 w-11",
};

/** Organization logo + display name for sidebar / top bar. */
export function OrgBrand({
  size = "md",
  showSlug = false,
  iconOnly = false,
  className,
  nameClassName,
}: {
  size?: Size;
  showSlug?: boolean;
  iconOnly?: boolean;
  className?: string;
  nameClassName?: string;
}) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);

  const { data: branding } = useQuery({
    queryKey: ["branding"],
    queryFn: () =>
      apiRequest<{ name: string; slug: string; has_logo: boolean }>("/api/v1/settings/branding", {
        token: accessToken,
      }),
    enabled: Boolean(accessToken && user && !user.is_platform_admin),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!branding || !user) return;
    if (user.tenant_name !== branding.name || Boolean(user.has_logo) !== branding.has_logo) {
      setUser({ ...user, tenant_name: branding.name, has_logo: branding.has_logo });
    }
  }, [branding, user, setUser]);

  const name = branding?.name || user?.tenant_name || "EmployeeMint";
  const hasLogo = Boolean(branding?.has_logo ?? user?.has_logo);

  useEffect(() => {
    let revoked: string | null = null;
    let cancelled = false;

    async function load() {
      if (!accessToken || !hasLogo) {
        setLogoUrl(null);
        return;
      }
      try {
        const blob = await apiDownload("/api/v1/settings/branding/logo", accessToken);
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        revoked = url;
        setLogoUrl(url);
      } catch {
        if (!cancelled) setLogoUrl(null);
      }
    }

    load();
    return () => {
      cancelled = true;
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [accessToken, hasLogo, branding?.name]);

  return (
    <div className={cn("flex min-w-0 items-center gap-3", className)}>
      {logoUrl ? (
        <img
          src={logoUrl}
          alt=""
          className={cn("shrink-0 rounded-lg object-contain bg-white", SIZE[size])}
        />
      ) : (
        <div
          className={cn(
            "flex shrink-0 items-center justify-center rounded-lg bg-brand-600 text-xs font-bold text-white",
            SIZE[size],
          )}
          aria-hidden
        >
          {name.slice(0, 2).toUpperCase()}
        </div>
      )}
      {!iconOnly && (
        <div className="min-w-0">
          <p className={cn("truncate font-bold text-brand-700", nameClassName)}>{name}</p>
          {showSlug && user?.tenant_slug && (
            <p className="truncate text-xs text-slate-500">{user.tenant_slug}</p>
          )}
        </div>
      )}
    </div>
  );
}
