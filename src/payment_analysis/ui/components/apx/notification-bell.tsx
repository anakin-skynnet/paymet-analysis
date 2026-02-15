/**
 * Notification bell — polls the backend for runtime warnings/errors.
 * Shows an unread count badge and a dropdown with recent notifications.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { Bell, AlertTriangle, XCircle, AlertOctagon, Check, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface Notification {
  id: string;
  timestamp: number;
  level: "warning" | "error" | "critical";
  source: string;
  message: string;
  read: boolean;
}

interface NotificationListResponse {
  notifications: Notification[];
  unread_count: number;
  total_count: number;
}

const POLL_INTERVAL = 15_000; // 15 seconds

const levelConfig = {
  warning: {
    icon: AlertTriangle,
    color: "text-yellow-500",
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/20",
    label: "Warning",
  },
  error: {
    icon: XCircle,
    color: "text-red-500",
    bg: "bg-red-500/10",
    border: "border-red-500/20",
    label: "Error",
  },
  critical: {
    icon: AlertOctagon,
    color: "text-red-600",
    bg: "bg-red-600/10",
    border: "border-red-600/20",
    label: "Critical",
  },
};

function timeAgo(ts: number): string {
  const diff = Math.floor(Date.now() / 1000 - ts);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function NotificationBell() {
  const [data, setData] = useState<NotificationListResponse | null>(null);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await fetch("/api/notifications?limit=30");
      if (res.ok) {
        const json: NotificationListResponse = await res.json();
        setData(json);
      }
    } catch {
      // Silently ignore — the bell just won't update
    }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      await fetch("/api/notifications/read-all", { method: "POST" });
      fetchNotifications();
    } catch {
      /* ignore */
    }
  }, [fetchNotifications]);

  // Poll
  useEffect(() => {
    fetchNotifications();
    const id = setInterval(fetchNotifications, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [fetchNotifications]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const unread = data?.unread_count ?? 0;
  const notifications = data?.notifications ?? [];

  return (
    <div ref={ref} className="relative">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="relative h-9 w-9"
            onClick={() => setOpen((o) => !o)}
            aria-label={`Notifications${unread > 0 ? ` (${unread} unread)` : ""}`}
          >
            <Bell className={cn("h-4 w-4", unread > 0 && "text-yellow-500")} />
            {unread > 0 && (
              <Badge
                variant="destructive"
                className="absolute -top-1 -right-1 h-4 min-w-4 px-1 text-[10px] leading-none flex items-center justify-center rounded-full"
              >
                {unread > 99 ? "99+" : unread}
              </Badge>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>Runtime notifications</TooltipContent>
      </Tooltip>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-[380px] max-h-[480px] bg-popover border border-border rounded-xl shadow-xl z-[100] flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-semibold">Notifications</span>
              {unread > 0 && (
                <Badge variant="secondary" className="text-[10px]">
                  {unread} new
                </Badge>
              )}
            </div>
            {unread > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs gap-1 text-muted-foreground hover:text-foreground"
                onClick={markAllRead}
              >
                <CheckCheck className="h-3 w-3" />
                Mark all read
              </Button>
            )}
          </div>

          {/* Notification list */}
          <div className="overflow-y-auto flex-1 scrollbar-thin">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
                <Check className="h-8 w-8 mb-2 opacity-40" />
                <p className="text-sm">No notifications</p>
                <p className="text-xs opacity-70 mt-0.5">System is running smoothly</p>
              </div>
            ) : (
              notifications.map((n) => {
                const config = levelConfig[n.level] || levelConfig.warning;
                const Icon = config.icon;
                return (
                  <div
                    key={n.id}
                    className={cn(
                      "px-4 py-3 border-b border-border/50 last:border-0 transition-colors",
                      !n.read && "bg-muted/20"
                    )}
                  >
                    <div className="flex gap-2.5">
                      <div
                        className={cn(
                          "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg mt-0.5",
                          config.bg,
                          config.border,
                          "border"
                        )}
                      >
                        <Icon className={cn("h-3.5 w-3.5", config.color)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge
                            variant="outline"
                            className={cn("text-[9px] h-4 px-1", config.color)}
                          >
                            {config.label}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground">
                            {n.source}
                          </span>
                          <span className="text-[10px] text-muted-foreground ml-auto shrink-0">
                            {timeAgo(n.timestamp)}
                          </span>
                          {!n.read && (
                            <span className="h-1.5 w-1.5 rounded-full bg-blue-500 shrink-0" />
                          )}
                        </div>
                        <p className="text-xs text-foreground/90 mt-1 leading-relaxed line-clamp-3">
                          {n.message}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="px-4 py-2 border-t border-border bg-muted/20 text-center">
              <span className="text-[10px] text-muted-foreground">
                Showing {notifications.length} of {data?.total_count ?? 0} notifications
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
