import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/auth";

export function TenantRouteGuard() {
  const user = useAuthStore((s) => s.user);
  const location = useLocation();

  const isSetupRoute = location.pathname.startsWith("/app/setup");

  if (user && !user.is_setup_complete && !isSetupRoute) {
    return <Navigate to="/app/setup" replace />;
  }

  if (user?.is_setup_complete && isSetupRoute) {
    return <Navigate to="/app/dashboard" replace />;
  }

  return <Outlet />;
}
