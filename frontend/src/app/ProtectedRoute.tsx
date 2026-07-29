import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/auth";

export function ProtectedRoute({ platform = false }: { platform?: boolean }) {
  const user = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.accessToken);

  if (!accessToken || !user) {
    return <Navigate to={platform ? "/platform/login" : "/login"} replace />;
  }

  if (platform && !user.is_platform_admin) {
    return <Navigate to="/app/dashboard" replace />;
  }

  if (!platform && user.is_platform_admin) {
    return <Navigate to="/platform/tenants" replace />;
  }

  return <Outlet />;
}
