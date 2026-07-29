import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Megaphone, Pause, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { apiRequest } from "@/api/client";
import { useAuthStore } from "@/store/auth";

interface Announcement {
  id: string;
  title: string;
  body: string;
  is_pinned: boolean;
}

const VISIBLE_KEY = "employeemint.announcementTicker.visible";
const SCROLL_KEY = "employeemint.announcementTicker.scroll";

function readBool(key: string, fallback: boolean) {
  try {
    const v = localStorage.getItem(key);
    if (v === null) return fallback;
    return v === "1" || v === "true";
  } catch {
    return fallback;
  }
}

export function AnnouncementTicker() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [visible, setVisible] = useState(() => readBool(VISIBLE_KEY, true));
  const [scrolling, setScrolling] = useState(() => readBool(SCROLL_KEY, true));

  useEffect(() => {
    try {
      localStorage.setItem(VISIBLE_KEY, visible ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [visible]);

  useEffect(() => {
    try {
      localStorage.setItem(SCROLL_KEY, scrolling ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [scrolling]);

  const { data } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () =>
      apiRequest<{ announcements: Announcement[] }>("/api/v1/dashboard/summary", {
        token: accessToken,
      }),
    select: (d) => d.announcements ?? [],
    staleTime: 60_000,
  });

  const items = data ?? [];
  if (!items.length) return null;

  if (!visible) {
    return (
      <div className="shrink-0 border-b border-brand-100 bg-brand-700">
        <button
          type="button"
          onClick={() => setVisible(true)}
          className="flex h-9 w-full items-center justify-center gap-2 px-3 text-xs font-medium text-white/90 hover:bg-brand-600 hover:text-white"
        >
          <Megaphone className="h-3.5 w-3.5 shrink-0" />
          Show announcements ({items.length})
          <ChevronDown className="h-3.5 w-3.5 shrink-0" />
        </button>
      </div>
    );
  }

  const track = [...items, ...items];

  return (
    <div className="announcement-ticker shrink-0 border-b border-brand-100 bg-brand-600 text-white">
      <div className="flex h-10 items-stretch">
        <div className="z-10 flex shrink-0 items-center gap-1.5 bg-brand-700 px-3 text-xs font-semibold uppercase tracking-wide">
          <Megaphone className="h-3.5 w-3.5 shrink-0" />
          News
        </div>
        <div className="relative flex min-w-0 flex-1 items-center overflow-hidden">
          <div
            className={`announcement-ticker-track flex w-max items-center gap-10 whitespace-nowrap pl-4 ${
              scrolling ? "" : "announcement-ticker-paused"
            }`}
          >
            {track.map((a, i) => (
              <span key={`${a.id}-${i}`} className="inline-flex items-center gap-2 text-sm leading-none">
                {a.is_pinned && (
                  <span className="rounded bg-white/20 px-1.5 py-0.5 text-[10px] font-bold uppercase leading-none">
                    Pinned
                  </span>
                )}
                <span className="font-semibold">{a.title}</span>
                <span className="text-white/85">{a.body}</span>
                <span className="text-white/40" aria-hidden>
                  •
                </span>
              </span>
            ))}
          </div>
        </div>
        <div className="z-10 flex shrink-0 items-center gap-1 bg-brand-700 px-2">
          <button
            type="button"
            onClick={() => setScrolling((s) => !s)}
            className="inline-flex h-7 items-center gap-1 rounded px-2 text-xs font-medium text-white/90 hover:bg-brand-600 hover:text-white"
            title={scrolling ? "Pause scroll" : "Resume scroll"}
          >
            {scrolling ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{scrolling ? "Pause" : "Play"}</span>
          </button>
          <button
            type="button"
            onClick={() => setVisible(false)}
            className="inline-flex h-7 items-center gap-1 rounded px-2 text-xs font-medium text-white/90 hover:bg-brand-600 hover:text-white"
            title="Hide announcements"
          >
            <ChevronUp className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Hide</span>
          </button>
        </div>
      </div>
    </div>
  );
}
