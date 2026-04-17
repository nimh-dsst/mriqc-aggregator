export type ViewId = "raw" | "exact" | "series"

export type MetricDescriptor = {
  field: string
  label: string
  family: string
  subfamily: string
  unit_hint: string | null
}

export type ModalityDescriptor = {
  name: string
  distribution_fields: string[]
  metric_fields: string[]
  metrics: MetricDescriptor[]
  extra_fields: string[]
}

export type MetricSummary = {
  field: string
  value_count: number
  missing_count: number
  missing_fraction: number
  min: number | null
  max: number | null
  mean: number | null
}

export type MetricHistogramBucket = {
  start: number
  end: number
  count: number
}

export type MetricDistribution = {
  field: string
  row_count: number
  value_count: number
  missing_count: number
  missing_fraction: number
  min: number | null
  max: number | null
  mean: number | null
  stddev: number | null
  quantiles: {
    p05: number | null
    p25: number | null
    p50: number | null
    p75: number | null
    p95: number | null
  }
  histogram: MetricHistogramBucket[]
}

export type MetricCatalog = ModalityDescriptor[]

export type ModalityId = ModalityDescriptor["name"]

export type MetricId = MetricDescriptor["field"]

export const VIEW_OPTIONS: ViewId[] = ["series", "raw", "exact"]
