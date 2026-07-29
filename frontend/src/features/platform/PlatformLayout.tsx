import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/store/auth";

export function PlatformLayout({ children }: { children: ReactNode }) {
  const logout = useAuthStore((s) => s.logout);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-6">
            <Link to="/platform/tenants" className="text-xl font-bold text-slate-900">
              EmployeeMint Platform
            </Link>
            <nav className="flex gap-4 text-sm">
              <Link to="/platform/tenants" className="text-slate-600 hover:text-slate-900">
                Tenants
              </Link>
            </nav>
          </div>
          <Button variant="ghost" onClick={logout}>
            Logout
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
