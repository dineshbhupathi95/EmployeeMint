import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, LogOut, Palette, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiRequest } from "@/api/client";
import { OrgBrand } from "@/components/OrgBrand";
import { UserAvatar } from "@/components/UserAvatar";
import { cn } from "@/lib/utils";
import { notificationRoute } from "@/lib/notificationRoutes";
import { useAuthStore } from "@/store/auth";
import { THEMES, useThemeStore } from "@/store/theme";

interface Notification {
  id: string;
  title: string;
  body: string;
  is_read: boolean;
  notification_type: string;
  metadata?: { request_type?: string; request_id?: string };
  created_at: string;
}

export function TopBar() {
  const navigate = useNavigate();
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const queryClient = useQueryClient();

  const [notifOpen, setNotifOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  const { data: unread } = useQuery({
    queryKey: ["notifications-unread"],
    queryFn: () => apiRequest<{ count: number }>("/api/v1/settings/notifications/unread-count", { token: accessToken }),
    refetchInterval: 30_000,
  });

  const { data: notifications } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => apiRequest<Notification[]>("/api/v1/settings/notifications", { token: accessToken }),
    enabled: notifOpen,
  });

  const markRead = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`/api/v1/settings/notifications/${id}/read`, { method: "POST", token: accessToken }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
    },
  });

  const markAllRead = useMutation({
    mutationFn: () =>
      apiRequest("/api/v1/settings/notifications/read-all", { method: "POST", token: accessToken }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
    },
  });

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
      if (userRef.current && !userRef.current.contains(e.target as Node)) setUserOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleNotificationClick = (n: Notification) => {
    if (!n.is_read) markRead.mutate(n.id);
    setNotifOpen(false);
    navigate(notificationRoute(n.notification_type, n.metadata));
  };

  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white/95 px-4 sm:px-6 backdrop-blur">
      <OrgBrand size="sm" className="min-w-0 flex-1" nameClassName="text-sm font-semibold text-slate-800" />
      <div className="flex shrink-0 items-center gap-1 sm:gap-2">
        {/* Notifications */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100"
            aria-label="Notifications"
          >
            <Bell className="h-5 w-5" />
            {(unread?.count ?? 0) > 0 && (
              <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                {unread!.count > 9 ? "9+" : unread!.count}
              </span>
            )}
          </button>
          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 rounded-xl border border-slate-200 bg-white shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <p className="font-semibold text-slate-900">Notifications</p>
                {(unread?.count ?? 0) > 0 && (
                  <button onClick={() => markAllRead.mutate()} className="text-xs text-brand-600 hover:underline">
                    Mark all read
                  </button>
                )}
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifications?.length ? notifications.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={cn(
                      "w-full border-b border-slate-50 px-4 py-3 text-left hover:bg-slate-50",
                      !n.is_read && "bg-brand-50/50",
                    )}
                  >
                    <p className="text-sm font-medium text-slate-900">{n.title}</p>
                    <p className="mt-0.5 text-xs text-slate-500 line-clamp-2">{n.body}</p>
                    <p className="mt-1 text-[10px] text-slate-400">
                      {new Date(n.created_at).toLocaleString()}
                    </p>
                  </button>
                )) : (
                  <p className="px-4 py-8 text-center text-sm text-slate-500">No notifications yet</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* User menu */}
        <div className="relative" ref={userRef}>
          <button
            onClick={() => setUserOpen(!userOpen)}
            className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100"
          >
            <UserAvatar size="sm" />
            <span className="hidden text-sm font-medium text-slate-700 sm:block">
              {user?.full_name?.split(" ")[0] ?? user?.email}
            </span>
          </button>
          {userOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white py-1 shadow-xl">
              <div className="border-b border-slate-100 px-4 py-3">
                <p className="text-sm font-medium text-slate-900">{user?.full_name}</p>
                <p className="text-xs text-slate-500">{user?.email}</p>
              </div>
              <Link
                to="/app/profile"
                onClick={() => setUserOpen(false)}
                className="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
              >
                <User className="h-4 w-4" /> Edit Profile
              </Link>
              <div className="border-t border-slate-100 px-4 py-2">
                <p className="mb-2 flex items-center gap-1 text-xs font-medium uppercase text-slate-400">
                  <Palette className="h-3 w-3" /> Theme
                </p>
                <div className="flex gap-2">
                  {THEMES.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      title={t.label}
                      onClick={() => setTheme(t.id)}
                      className={cn(
                        "h-7 w-7 rounded-full border-2 transition-transform hover:scale-110",
                        theme === t.id ? "border-slate-900" : "border-transparent",
                      )}
                      style={{ backgroundColor: t.swatch }}
                    />
                  ))}
                </div>
              </div>
              <button
                onClick={logout}
                className="flex w-full items-center gap-2 border-t border-slate-100 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
              >
                <LogOut className="h-4 w-4" /> Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
