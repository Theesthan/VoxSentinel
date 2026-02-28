import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center px-2 py-0.5 text-[10px] font-medium tracking-wider uppercase transition-colors",
  {
    variants: {
      variant: {
        default: "border border-white/10 text-white/60",
        success: "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
        warning: "border border-amber-500/30 bg-amber-500/10 text-amber-400",
        danger: "border border-red-500/30 bg-red-500/10 text-red-400",
        info: "border border-blue-500/30 bg-blue-500/10 text-blue-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
