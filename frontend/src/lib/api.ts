import type {
  DashboardFilters,
  MetricCatalog,
  MetricDistribution,
  MetricSummary,
  ValueDistribution,
  ViewId,
} from "@/types/ui"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "/api/v1"
const RESPONSE_TTL_MS = 5 * 60 * 1000
const MAX_CACHE_ENTRIES = 128

type CacheEntry = {
  expiresAt: number
  value: unknown
}

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

type ValueDistributionResponse = {
  modality: string
  field: string
  view: ViewId
  filters: Record<string, unknown>
  values: ValueDistribution[]
}

const responseCache = new Map<string, CacheEntry>()
const inflightRequests = new Map<string, Promise<unknown>>()

function pruneCache(now: number) {
  for (const [key, entry] of responseCache.entries()) {
    if (entry.expiresAt <= now) {
      responseCache.delete(key)
    }
  }

  while (responseCache.size > MAX_CACHE_ENTRIES) {
    const oldestKey = responseCache.keys().next().value
    if (!oldestKey) {
      break
    }
    responseCache.delete(oldestKey)
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  const url = `${API_BASE_URL}${path}`
  const now = Date.now()
  const cached = responseCache.get(url)
  if (cached && cached.expiresAt > now) {
    return cached.value as T
  }

  const inflight = inflightRequests.get(url)
  if (inflight) {
    return inflight as Promise<T>
  }

  const request = fetch(url).then(async (response) => {
    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}`)
    }

    const payload = (await response.json()) as T
    responseCache.set(url, {
      expiresAt: Date.now() + RESPONSE_TTL_MS,
      value: payload,
    })
    pruneCache(Date.now())
    return payload
  })

  inflightRequests.set(url, request)
  try {
    return await request
  } finally {
    inflightRequests.delete(url)
  }
}

function buildFiltersQuery(filters: DashboardFilters) {
  const params = new URLSearchParams()

  for (const manufacturer of filters.manufacturers) {
    params.append("manufacturers", manufacturer)
  }
  for (const version of filters.mriqcVersions) {
    params.append("mriqc_versions", version)
  }
  for (const taskId of filters.taskIds) {
    params.append("task_ids", taskId)
  }
  if (filters.sourceCreatedFrom) {
    params.set("source_created_from", filters.sourceCreatedFrom)
  }
  if (filters.sourceCreatedTo) {
    params.set("source_created_to", filters.sourceCreatedTo)
  }

  return params
}

function appendQuery(path: string, params: URLSearchParams) {
  const query = params.toString()
  return query ? `${path}?${query}` : path
}

export async function fetchModalities(): Promise<MetricCatalog> {
  const payload = await fetchJson<ModalitiesResponse>("/modalities")
  return payload.modalities
}

export async function fetchMetricSummaries(
  modality: string,
  view: ViewId,
  filters: DashboardFilters
): Promise<MetricSummary[]> {
  const params = buildFiltersQuery(filters)
  params.set("view", view)
  const payload = await fetchJson<MetricSummariesResponse>(
    appendQuery(`/modalities/${modality}/metrics`, params)
  )
  return payload.metrics
}

export async function fetchMetricDistribution(
  modality: string,
  fieldName: string,
  view: ViewId,
  filters: DashboardFilters,
  bins = 24
): Promise<MetricDistribution> {
  const params = buildFiltersQuery(filters)
  params.set("view", view)
  params.set("bins", String(bins))
  const payload = await fetchJson<MetricDistributionResponse>(
    appendQuery(`/modalities/${modality}/metrics/${fieldName}`, params)
  )
  return payload.distribution
}

export async function fetchValueDistribution(
  modality: string,
  fieldName: string,
  view: ViewId,
  filters: DashboardFilters,
  limit = 24
): Promise<ValueDistribution[]> {
  const params = buildFiltersQuery(filters)
  params.set("view", view)
  params.set("limit", String(limit))
  const payload = await fetchJson<ValueDistributionResponse>(
    appendQuery(`/modalities/${modality}/distributions/${fieldName}`, params)
  )
  return payload.values
}
