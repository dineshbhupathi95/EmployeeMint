import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface UserInfo {
  id: string;
  email: string;
  tenant_id?: string | null;
  tenant_slug?: string | null;
  tenant_name?: string | null;
  has_logo?: boolean;
  employee_id?: string | null;
  employee_code?: string | null;
  full_name?: string | null;
  phone?: string | null;
  work_email?: string | null;
  has_avatar?: boolean;
  permissions: string[];
  is_platform_admin?: boolean;
  is_setup_complete?: boolean;
  is_impersonation?: boolean;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserInfo | null;
  setAuth: (tokens: { access_token: string; refresh_token: string }, user: UserInfo) => void;
  setUser: (user: UserInfo) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setAuth: (tokens, user) =>
        set({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          user,
        }),
      setUser: (user) => set({ user }),
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    { name: "employeemint-auth" },
  ),
);
