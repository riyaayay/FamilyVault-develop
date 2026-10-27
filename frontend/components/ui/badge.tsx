import * as React from "react";
import { cn } from "@/lib/utils";

const statusStyles = {
  upcoming: "bg-secondary text-secondary-foreground",
  overdue: "bg-destructive/10 text-destructive",
  done: "bg-accent text-accent-foreground",
  joint_clan: "border border-border text-muted-foreground",
  nuclear_household: "border border-border text-foreground",
  private_strict: "border border-destructive/40 text-destructive",
} as const;

type BadgeStatus = keyof typeof statusStyles;

function Badge({
  className,
  status = "upcoming",
  ...props
}: React.ComponentProps<"span"> & { status?: BadgeStatus }) {
  return (
    <span
      data-slot="badge"
      data-status={status}
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium capitalize",
        statusStyles[status],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
