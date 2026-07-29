import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useAuthStore } from "@/store/auth";

interface AuthResponse {
  tokens: { access_token: string; refresh_token: string; token_type: string };
  user: {
    id: string;
    email: string;
    tenant_id?: string;
    tenant_slug?: string;
    full_name?: string;
    permissions: string[];
    is_platform_admin?: boolean;
    is_setup_complete?: boolean;
  };
}

export function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantSlug, setTenantSlug] = useState("");
  const [error, setError] = useState("");

  const loginMutation = useMutation({
    mutationFn: () =>
      apiRequest<AuthResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          tenant_slug: tenantSlug || null,
        }),
      }),
    onSuccess: (data) => {
      setAuth(data.tokens, data.user);
      navigate(data.user.is_setup_complete ? "/app/dashboard" : "/app/setup");
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-brand-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader
          title="Sign in to EmployeeMint"
          description="Enter your credentials to access your HR portal"
        />
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            setError("");
            loginMutation.mutate();
          }}
        >
          <Input
            id="tenant"
            label="Company slug"
            placeholder="acme"
            value={tenantSlug}
            onChange={(e) => setTenantSlug(e.target.value)}
          />
          <Input
            id="email"
            label="Email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            id="password"
            label="Password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "Signing in..." : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-500">
          Platform admin?{" "}
          <a href="/platform/login" className="text-brand-600 hover:underline">
            Sign in here
          </a>
        </p>
      </Card>
    </div>
  );
}
