import { useEffect, useState } from "react";
import { apiDownload } from "@/api/client";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

/** Loads the current user's avatar with auth and shows initials as fallback. */
export function UserAvatar({
  size = "md",
  className,
  name,
}: {
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
  name?: string | null;
}) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const hasAvatar = user?.has_avatar;
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!hasAvatar || !accessToken) {
      setUrl(null);
      return;
    }
    let active = true;
    let objectUrl: string | null = null;
    apiDownload("/api/v1/auth/me/avatar", accessToken)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (active) setUrl(null);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [hasAvatar, accessToken, user]);

  const sizes = {
    sm: "h-8 w-8 text-xs",
    md: "h-10 w-10 text-sm",
    lg: "h-16 w-16 text-xl",
    xl: "h-24 w-24 text-2xl",
  };

  const displayName = name ?? user?.full_name ?? user?.email ?? "?";
  const initials = displayName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  if (url) {
    return (
      <img
        src={url}
        alt={displayName}
        className={cn("rounded-full object-cover", sizes[size], className)}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 font-bold text-white",
        sizes[size],
        className,
      )}
    >
      {initials}
    </div>
  );
}
