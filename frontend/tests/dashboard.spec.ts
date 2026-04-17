import { expect, test } from "@playwright/test"

const metrics = [
  {
    field: "cjv",
    label: "CJV",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "cnr",
    label: "CNR",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "efc",
    label: "EFC",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "fber",
    label: "FBER",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "fwhm_avg",
    label: "FWHM Avg",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "inu_med",
    label: "INU Median",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "qi_1",
    label: "QI 1",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "qi_2",
    label: "QI 2",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "snr_csf",
    label: "SNR CSF",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "snr_gm",
    label: "SNR GM",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "snr_total",
    label: "SNR Total",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "snr_wm",
    label: "SNR WM",
    family: "Image Quality",
    subfamily: "Extremely Long Category Name To Stress The Sidebar Layout",
    unit_hint: null,
  },
  {
    field: "wm2max",
    label: "WM2MAX",
    family: "Image Quality",
    subfamily: "Short Category",
    unit_hint: null,
  },
]

const summaries = metrics.map((metric, index) => ({
  field: metric.field,
  value_count: 1000 - index,
  missing_count: 0,
  missing_fraction: 0,
  min: 0.1,
  max: 0.9,
  mean: 0.5,
}))

const distribution = {
  field: "cjv",
  row_count: 1000,
  value_count: 1000,
  missing_count: 0,
  missing_fraction: 0,
  min: 0.1,
  max: 0.9,
  mean: 0.5,
  stddev: 0.1,
  quantiles: {
    p05: 0.15,
    p25: 0.3,
    p50: 0.5,
    p75: 0.7,
    p95: 0.85,
  },
  histogram: [
    { start: 0.1, end: 0.2, count: 80 },
    { start: 0.2, end: 0.3, count: 120 },
    { start: 0.3, end: 0.4, count: 180 },
    { start: 0.4, end: 0.5, count: 240 },
    { start: 0.5, end: 0.6, count: 180 },
    { start: 0.6, end: 0.7, count: 120 },
    { start: 0.7, end: 0.8, count: 60 },
    { start: 0.8, end: 0.9, count: 20 },
  ],
}

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/modalities", async (route) => {
    await route.fulfill({
      json: {
        modalities: [
          {
            name: "bold",
            distribution_fields: metrics.map((metric) => metric.field),
            metric_fields: metrics.map((metric) => metric.field),
            metrics,
            extra_fields: [],
          },
        ],
      },
    })
  })

  await page.route("**/api/v1/modalities/bold/metrics?view=series", async (route) => {
    await route.fulfill({
      json: {
        modality: "bold",
        view: "series",
        filters: {},
        metrics: summaries,
      },
    })
  })

  await page.route("**/api/v1/modalities/bold/metrics/*", async (route) => {
    const url = new URL(route.request().url())
    const field = url.pathname.split("/").pop() ?? distribution.field
    await route.fulfill({
      json: {
        modality: "bold",
        field,
        view: "series",
        filters: {},
        distribution: {
          ...distribution,
          field,
        },
      },
    })
  })
})

test("category counts stay aligned and do not overlap the chevron", async ({ page }) => {
  await page.goto("/")

  const categoryRow = page
    .getByRole("button", {
      name: /Extremely Long Category Name To Stress The Sidebar Layout/i,
    })
    .first()

  await expect(categoryRow).toBeVisible()

  const badge = categoryRow.getByText("12", { exact: true })
  const chevron = categoryRow.locator("svg.lucide-chevron-right")

  await expect(badge).toBeVisible()
  await expect(chevron).toBeVisible()

  const badgeBox = await badge.boundingBox()
  const chevronBox = await chevron.boundingBox()

  expect(badgeBox).not.toBeNull()
  expect(chevronBox).not.toBeNull()
  expect(badgeBox!.x + badgeBox!.width + 4).toBeLessThan(chevronBox!.x)
})

test("dashboard renders and supports core interactions", async ({ page }) => {
  await page.goto("/")

  await expect(page.getByText("MRIQC Aggregator")).toBeVisible()
  await expect(page.getByRole("button", { name: /deduplicated/i })).toBeVisible()
  await expect(page.getByRole("heading", { name: "CJV" })).toBeVisible()

  await page.getByPlaceholder("Search measures...").fill("snr")
  await expect(page.getByText("SNR CSF")).toBeVisible()

  await page.getByRole("button", { name: /select all/i }).click()
  await expect(page.getByText(/bold · 12 selected metrics/i)).toBeVisible()

  const cards = page.locator("section").filter({ has: page.getByText("Samples") })
  await expect(cards).toHaveCount(12)

  await page.getByRole("button", { name: /collapse all/i }).click()

  const tooltipButton = page.locator('button[aria-label^="About "]').first()
  await tooltipButton.hover()
  await expect(page.locator('[data-slot="tooltip-content"]').first()).toBeVisible()
})
