import type { ReactNode } from "react";
import { usePermission } from "@/hooks/usePermission";

interface CanProps {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
}

export function Can({ permission, children, fallback = null }: CanProps) {
  const allowed = usePermission(permission);
  return allowed ? <>{children}</> : <>{fallback}</>;
}
