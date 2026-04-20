import { SlidersHorizontalIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { DashboardFilters, ValueDistribution } from "@/types/ui"

function formatFilterSummary(selected: string[], total: number, emptyLabel: string) {
  if (selected.length === 0) {
    return emptyLabel
  }

  if (selected.length === total) {
    return "All"
  }

  if (selected.length === 1) {
    return selected[0]
  }

  return `${selected.length} selected`
}

function FilterDropdown({
  label,
  emptyLabel,
  selected,
  options,
  onChange,
}: {
  label: string
  emptyLabel: string
  selected: string[]
  options: ValueDistribution[]
  onChange: (nextValues: string[]) => void
}) {
  if (!options.length) {
    return null
  }

  const selectedSet = new Set(selected)
  const optionValues = options.map((option) => option.value)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="outline" size="sm" className="rounded-full">
          {label}: {formatFilterSummary(selected, optionValues.length, emptyLabel)}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72">
        <DropdownMenuLabel>{label}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => onChange(optionValues)}>Select all</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => onChange([])}>Clear</DropdownMenuItem>
        <DropdownMenuSeparator />
        {options.map((option) => (
          <DropdownMenuCheckboxItem
            key={option.value}
            checked={selectedSet.has(option.value)}
            onCheckedChange={(checked) => {
              if (checked) {
                onChange([...selected, option.value])
                return
              }
              onChange(selected.filter((value) => value !== option.value))
            }}
          >
            <span className="truncate">{option.value}</span>
            <span className="ml-auto pl-4 text-xs text-muted-foreground">{option.count}</span>
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function DashboardFiltersBar({
  filters,
  manufacturerOptions,
  versionOptions,
  taskOptions,
  onChange,
  onReset,
}: {
  filters: DashboardFilters
  manufacturerOptions: ValueDistribution[]
  versionOptions: ValueDistribution[]
  taskOptions: ValueDistribution[]
  onChange: (nextFilters: DashboardFilters) => void
  onReset: () => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/75 px-3 py-1 text-xs font-medium text-muted-foreground">
        <SlidersHorizontalIcon className="size-3.5" />
        Filters
      </span>
      <FilterDropdown
        label="Manufacturer"
        emptyLabel="Any"
        selected={filters.manufacturers}
        options={manufacturerOptions}
        onChange={(manufacturers) => onChange({ ...filters, manufacturers })}
      />
      <FilterDropdown
        label="MRIQC version"
        emptyLabel="Any"
        selected={filters.mriqcVersions}
        options={versionOptions}
        onChange={(mriqcVersions) => onChange({ ...filters, mriqcVersions })}
      />
      <FilterDropdown
        label="Task"
        emptyLabel="Any"
        selected={filters.taskIds}
        options={taskOptions}
        onChange={(taskIds) => onChange({ ...filters, taskIds })}
      />
      <label className="flex items-center gap-2 rounded-full border border-border/70 bg-background/75 px-3 py-1 text-xs text-muted-foreground">
        From
        <input
          type="date"
          className="bg-transparent text-foreground outline-none"
          value={filters.sourceCreatedFrom?.slice(0, 10) ?? ""}
          onChange={(event) =>
            onChange({
              ...filters,
              sourceCreatedFrom: event.target.value ? `${event.target.value}T00:00:00Z` : null,
            })
          }
        />
      </label>
      <label className="flex items-center gap-2 rounded-full border border-border/70 bg-background/75 px-3 py-1 text-xs text-muted-foreground">
        To
        <input
          type="date"
          className="bg-transparent text-foreground outline-none"
          value={filters.sourceCreatedTo?.slice(0, 10) ?? ""}
          onChange={(event) =>
            onChange({
              ...filters,
              sourceCreatedTo: event.target.value ? `${event.target.value}T23:59:59Z` : null,
            })
          }
        />
      </label>
      <Button type="button" variant="ghost" size="sm" className="rounded-full" onClick={onReset}>
        Reset
      </Button>
    </div>
  )
}
