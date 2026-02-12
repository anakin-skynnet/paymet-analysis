"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { DashboardInfo } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ExternalLink, LayoutGrid } from "lucide-react";

const categoryVariant: Record<string, "default" | "secondary" | "outline"> = {
  executive: "default",
  operations: "secondary",
  analytics: "secondary",
  technical: "outline",
};

export interface DashboardTableProps {
  /** Dashboards from API (useListDashboards) or mock when backend unavailable. */
  dashboards: DashboardInfo[];
  /** Optional: show loading skeleton instead of table. */
  isLoading?: boolean;
  /** Optional: callback to open dashboard in app (embed). */
  onViewInApp?: (id: string) => void;
  /** Optional: callback to open dashboard in new tab. */
  onOpenInTab?: (dashboard: DashboardInfo) => void;
  className?: string;
}

export function DashboardTable({
  dashboards,
  isLoading = false,
  onViewInApp,
  onOpenInTab,
  className,
}: DashboardTableProps) {
  if (isLoading) {
    return (
      <Card className={cn("border border-border/80", className)}>
        <CardHeader>
          <CardTitle className="text-base">Dashboards</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-10 rounded-md bg-muted/50 animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("border border-border/80 overflow-hidden", className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">All dashboards</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-auto max-h-[60vh]">
          <Table>
            <TableHeader>
              <TableRow className="border-border/80 hover:bg-transparent">
                <TableHead className="font-medium text-muted-foreground">Name</TableHead>
                <TableHead className="font-medium text-muted-foreground">Category</TableHead>
                <TableHead className="font-medium text-muted-foreground hidden md:table-cell">Description</TableHead>
                <TableHead className="font-medium text-muted-foreground text-right w-[140px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {dashboards.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                    No dashboards available.
                  </TableCell>
                </TableRow>
              ) : (
                dashboards.map((d) => (
                  <TableRow key={d.id} className="border-border/80">
                    <TableCell className="font-medium">{d.name}</TableCell>
                    <TableCell>
                      <Badge variant={categoryVariant[d.category] ?? "outline"} className="capitalize">
                        {d.category}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm max-w-[240px] truncate hidden md:table-cell">
                      {d.description}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        {onViewInApp && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8"
                            onClick={() => onViewInApp(d.id)}
                          >
                            <LayoutGrid className="h-3.5 w-3.5 mr-1" />
                            In app
                          </Button>
                        )}
                        {onOpenInTab && d.url_path && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8"
                            onClick={() => onOpenInTab(d)}
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
