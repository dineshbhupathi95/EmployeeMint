import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useAuthStore } from "@/store/auth";

interface AuthResponse {
  tokens: { access_token: string; refresh_token: string };
  user: {
    id: string;
    email: string;
    permissions: string[];
    is_platform_admin: boolean;
    full_name?: string;
  };
}

export function PlatformLoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const loginMutation = useMutation({
    mutationFn: () =>
      apiRequest<AuthResponse>("/api/v1/auth/platform/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    onSuccess: (data) => {
      setAuth(data.tokens, data.user);
      navigate("/platform/tenants");
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-900 p-4">
      <Card className="w-full max-w-md">
        <CardHeader
          title="Platform Admin"
          description="Manage tenants and platform settings"
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
      </Card>
    </div>
  );
}
