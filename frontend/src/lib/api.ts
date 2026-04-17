import type {
  MetricCatalog,
  MetricDistribution,
  MetricSummary,
  ViewId,
} from "@/types/ui"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "/api/v1"

type MetricDistributionResponse = {
  modality: string
  field: string
  view: ViewId
  filters: Record<string, unknown>
  distribution: MetricDistribution
}

type ModalitiesResponse = {
  modalities: MetricCatalog
}

type MetricSummariesResponse = {
  modality: string
  view: ViewId
  filters: Record<string, unknown>
  metrics: MetricSummary[]
}

export async function fetchModalities(): Promise<MetricCatalog> {
  const response = await fetch(`${API_BASE_URL}/modalities`)

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`)
  }

  const payload = (await response.json()) as ModalitiesResponse
  return payload.modalities
}

export async function fetchMetricSummaries(
  modality: string,
  view: ViewId
): Promise<MetricSummary[]> {
  const response = await fetch(
    `${API_BASE_URL}/modalities/${modality}/metrics?view=${view}`
  )

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`)
  }

  const payload = (await response.json()) as MetricSummariesResponse
  return payload.metrics
}

export async function fetchMetricDistribution(
  modality: string,
  fieldName: string,
  view: ViewId,
  bins = 24
): Promise<MetricDistribution> {
  const response = await fetch(
    `${API_BASE_URL}/modalities/${modality}/metrics/${fieldName}?view=${view}&bins=${bins}`
  )

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`)
  }

  const payload = (await response.json()) as MetricDistributionResponse
  return payload.distribution
}
