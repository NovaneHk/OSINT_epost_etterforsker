import React from "react"
import { cn } from "@/lib/utils"

export type CalendarProps = {
  className?: string;
  mode?: "single" | "range";
  selected?: Date | { from?: Date; to?: Date };
  onSelect?: (value: any) => void;
}

function Calendar({
  className,
  mode = "single",
  selected,
  onSelect,
  ...props
}: CalendarProps) {
  return (
    <div className={cn("p-3 border rounded-md", className)}>
      <div className="text-sm text-muted-foreground">
        Kalenderfunksjon er midlertidig deaktivert
      </div>
      <input
        type="date"
        className="w-full p-2 mt-2 border rounded"
        onChange={(e) => onSelect?.(new Date(e.target.value))}
      />
    </div>
  )
}
Calendar.displayName = "Calendar"

export { Calendar }