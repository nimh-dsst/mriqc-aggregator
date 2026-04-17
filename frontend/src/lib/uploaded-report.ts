import type {
  MetricCatalog,
  MetricDistribution,
  MetricSummary,
  ModalityId,
} from "@/types/ui"

type UploadedRow = Record<string, string>

export type UploadedFileDraft = {
  id: string
  file: File
  fileName: string
  rowCount: number
  detectedModality: ModalityId | null
  selectedModality: ModalityId | null
}

export type UploadedModalityReport = {
  modality: ModalityId
  fileName: string
  rowCount: number
  summaries: MetricSummary[]
  distributions: Record<string, MetricDistribution>
}

export type UploadedReportBundle = {
  modalities: Partial<Record<ModalityId, UploadedModalityReport>>
}

type ParsedFile = {
  file: File
  fileName: string
  rows: UploadedRow[]
  headers: string[]
}

const BOLD_HINT_FIELDS = new Set([
  "task_id",
  "dummy_trs",
  "dvars_nstd",
  "fd_mean",
  "tsnr",
])

function inferModality(fileName: string, headers: string[]): ModalityId | null {
  const normalizedName = fileName.toLowerCase()
  if (normalizedName.includes("t1w")) {
    return "T1w"
  }
  if (normalizedName.includes("t2w")) {
    return "T2w"
  }
  if (normalizedName.includes("bold")) {
    return "bold"
  }

  if (headers.some((header) => BOLD_HINT_FIELDS.has(header))) {
    return "bold"
  }

  return null
}

function parseCsv(text: string): UploadedRow[] {
  const rows: string[][] = []
  let field = ""
  let row: string[] = []
  let inQuotes = false

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index]
    const nextChar = text[index + 1]

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        field += '"'
        index += 1
      } else {
        inQuotes = !inQuotes
      }
      continue
    }

    if (char === "," && !inQuotes) {
      row.push(field)
      field = ""
      continue
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && nextChar === "\n") {
        index += 1
      }
      row.push(field)
      field = ""
      if (row.some((value) => value.length > 0)) {
        rows.push(row)
      }
      row = []
      continue
    }

    field += char
  }

  if (field.length > 0 || row.length > 0) {
    row.push(field)
    if (row.some((value) => value.length > 0)) {
      rows.push(row)
    }
  }

  if (rows.length === 0) {
    return []
  }

  const [headers, ...values] = rows
  return values.map((record) =>
    Object.fromEntries(headers.map((header, index) => [header, record[index] ?? ""]))
  )
}

function toNumber(value: string | undefined): number | null {
  if (value === undefined) {
    return null
  }

  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }

  const numeric = Number(trimmed)
  return Number.isFinite(numeric) ? numeric : null
}

function quantile(sortedValues: number[], probability: number): number | null {
  if (sortedValues.length === 0) {
    return null
  }

  if (sortedValues.length === 1) {
    return sortedValues[0]
  }

  const index = (sortedValues.length - 1) * probability
  const lower = Math.floor(index)
  const upper = Math.ceil(index)

  if (lower === upper) {
    return sortedValues[lower]
  }

  const fraction = index - lower
  return sortedValues[lower] + (sortedValues[upper] - sortedValues[lower]) * fraction
}

function buildHistogram(values: number[], maxBins = 24) {
  if (values.length === 0) {
    return []
  }

  const min = values[0]
  const max = values[values.length - 1]
  if (min === max) {
    return [{ start: min, end: max, count: values.length }]
  }

  const binCount = Math.min(maxBins, Math.max(1, Math.round(Math.sqrt(values.length))))
  const width = (max - min) / binCount
  const counts = new Array(binCount).fill(0)

  for (const value of values) {
    const rawIndex = Math.floor((value - min) / width)
    const bucketIndex = Math.min(binCount - 1, Math.max(0, rawIndex))
    counts[bucketIndex] += 1
  }

  return counts.map((count, index) => ({
    start: min + width * index,
    end: index === binCount - 1 ? max : min + width * (index + 1),
    count,
  }))
}

function buildDistribution(
  field: string,
  values: number[],
  rowCount: number
): MetricDistribution {
  const valueCount = values.length
  const missingCount = rowCount - valueCount

  if (valueCount === 0) {
    return {
      field,
      row_count: rowCount,
      value_count: 0,
      missing_count: missingCount,
      missing_fraction: rowCount === 0 ? 0 : missingCount / rowCount,
      min: null,
      max: null,
      mean: null,
      stddev: null,
      quantiles: { p05: null, p25: null, p50: null, p75: null, p95: null },
      histogram: [],
    }
  }

  const sortedValues = [...values].sort((left, right) => left - right)
  const total = sortedValues.reduce((sum, value) => sum + value, 0)
  const mean = total / valueCount
  const variance =
    sortedValues.reduce((sum, value) => sum + (value - mean) ** 2, 0) / valueCount

  return {
    field,
    row_count: rowCount,
    value_count: valueCount,
    missing_count: missingCount,
    missing_fraction: rowCount === 0 ? 0 : missingCount / rowCount,
    min: sortedValues[0],
    max: sortedValues[valueCount - 1],
    mean,
    stddev: Math.sqrt(variance),
    quantiles: {
      p05: quantile(sortedValues, 0.05),
      p25: quantile(sortedValues, 0.25),
      p50: quantile(sortedValues, 0.5),
      p75: quantile(sortedValues, 0.75),
      p95: quantile(sortedValues, 0.95),
    },
    histogram: buildHistogram(sortedValues),
  }
}

async function parseFile(file: File): Promise<ParsedFile> {
  const rows = parseCsv(await file.text())
  if (rows.length === 0) {
    throw new Error(`"${file.name}" is empty or could not be parsed as CSV.`)
  }

  const headers = Object.keys(rows[0])
  return {
    file,
    fileName: file.name,
    rows,
    headers,
  }
}

function buildModalityReport(
  parsedFile: ParsedFile,
  modality: ModalityId,
  catalog: MetricCatalog
): UploadedModalityReport {
  const metricFields = new Set(
    (catalog.find((entry) => entry.name === modality)?.metrics ?? []).map(
      (metric) => metric.field
    )
  )

  const distributions = Object.fromEntries(
    [...metricFields].map((field) => {
      const values = parsedFile.rows
        .map((row) => toNumber(row[field]))
        .filter((value): value is number => value !== null)

      return [field, buildDistribution(field, values, parsedFile.rows.length)]
    })
  )

  return {
    modality,
    fileName: parsedFile.fileName,
    rowCount: parsedFile.rows.length,
    summaries: Object.values(distributions).map((distribution) => ({
      field: distribution.field,
      value_count: distribution.value_count,
      missing_count: distribution.missing_count,
      missing_fraction: distribution.missing_fraction,
      min: distribution.min,
      max: distribution.max,
      mean: distribution.mean,
    })),
    distributions,
  }
}

export async function buildUploadDrafts(files: File[]): Promise<UploadedFileDraft[]> {
  const parsedFiles = await Promise.all(
    files
      .filter((file) => file.name.toLowerCase().endsWith(".csv"))
      .map((file) => parseFile(file))
  )

  if (parsedFiles.length === 0) {
    throw new Error("No MRIQC CSV files were provided.")
  }

  return parsedFiles.map((parsedFile, index) => {
    const detectedModality = inferModality(parsedFile.fileName, parsedFile.headers)
    return {
      id: `${parsedFile.fileName}-${index}`,
      file: parsedFile.file,
      fileName: parsedFile.fileName,
      rowCount: parsedFile.rows.length,
      detectedModality,
      selectedModality: detectedModality,
    }
  })
}

export async function finalizeUploadedReports(
  drafts: UploadedFileDraft[],
  catalog: MetricCatalog
): Promise<UploadedReportBundle> {
  if (drafts.length === 0) {
    throw new Error("Add at least one MRIQC CSV file before loading the dataset.")
  }

  const unresolvedDraft = drafts.find((draft) => draft.selectedModality === null)
  if (unresolvedDraft) {
    throw new Error(`Select a modality for "${unresolvedDraft.fileName}" before loading.`)
  }

  const parsedFiles = await Promise.all(
    drafts.map(async (draft) => ({
      draft,
      parsedFile: await parseFile(draft.file),
    }))
  )

  const modalities: Partial<Record<ModalityId, UploadedModalityReport>> = {}
  for (const { draft, parsedFile } of parsedFiles) {
    modalities[draft.selectedModality as ModalityId] = buildModalityReport(
      parsedFile,
      draft.selectedModality as ModalityId,
      catalog
    )
  }

  return { modalities }
}
