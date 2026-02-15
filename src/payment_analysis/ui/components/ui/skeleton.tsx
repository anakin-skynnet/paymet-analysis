import { cn } from "@/lib/utils"

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg bg-muted/80 dark:bg-muted",
        "before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_ease-in-out_infinite] before:bg-gradient-to-r before:from-transparent before:via-white/[0.08] dark:before:via-white/[0.06] before:to-transparent",
        className
      )}
      {...props}
    />
  )
}

export { Skeleton }
