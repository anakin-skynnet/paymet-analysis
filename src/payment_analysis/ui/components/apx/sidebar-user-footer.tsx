import { Suspense, useMemo } from "react";
import { SidebarMenuButton } from "@/components/ui/sidebar";
import { useCurrentUserSuspense, type User } from "@/lib/api";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBoundary } from "react-error-boundary";
import selector from "@/lib/selector";

function SidebarUserFooterSkeleton() {
  return (
    <SidebarMenuButton size="lg">
      <Skeleton className="h-8 w-8 rounded-lg" />
      <div className="grid flex-1 text-left text-sm leading-tight gap-1">
        <Skeleton className="h-4 w-24 rounded" />
        <Skeleton className="h-3 w-46 rounded" />
      </div>
    </SidebarMenuButton>
  );
}

/** Shown when current-user API fails (e.g. no Databricks token locally). */
function SidebarUserFooterFallback() {
  return (
    <SidebarMenuButton size="lg" className="opacity-70">
      <Avatar className="h-8 w-8 rounded-lg">
        <AvatarFallback className="rounded-lg text-xs">PA</AvatarFallback>
      </Avatar>
      <div className="grid flex-1 text-left text-sm leading-tight">
        <span className="truncate font-medium">Payment Analysis</span>
        <span className="text-muted-foreground truncate text-xs">
          Sign in via Databricks Apps
        </span>
      </div>
    </SidebarMenuButton>
  );
}

function SidebarUserFooterContent() {
  const { data: user } = useCurrentUserSuspense({
    query: { ...selector<User>().query, retry: false, staleTime: 5 * 60_000 },
  });

  const firstLetters = useMemo(() => {
    const userName = user.user_name ?? "";
    const [first = "", ...rest] = userName.split(" ");
    const last = rest.at(-1) ?? "";
    return `${first[0] ?? ""}${last[0] ?? ""}`.toUpperCase();
  }, [user.user_name]);

  return (
    <SidebarMenuButton
      size="lg"
      className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
    >
      <Avatar className="h-8 w-8 rounded-lg grayscale">
        <AvatarFallback className="rounded-lg">{firstLetters}</AvatarFallback>
      </Avatar>
      <div className="grid flex-1 text-left text-sm leading-tight">
        <span className="truncate font-medium">{user.display_name}</span>
        <span className="text-muted-foreground truncate text-xs">
          {user.user_name}
        </span>
      </div>
    </SidebarMenuButton>
  );
}

export default function SidebarUserFooter() {
  return (
    <ErrorBoundary fallback={<SidebarUserFooterFallback />}>
      <Suspense fallback={<SidebarUserFooterSkeleton />}>
        <SidebarUserFooterContent />
      </Suspense>
    </ErrorBoundary>
  );
}
