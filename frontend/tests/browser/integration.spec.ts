import { test, expect } from "@playwright/test";
import { mockApi, health } from "./fixtures";

test.beforeEach(async ({ page }) => mockApi(page));

test("structured retrieval carries known context and explains cross-service evidence", async ({
  page,
}) => {
  await page.goto("/#/memory");
  await page.getByText("Optional incident context", { exact: true }).click();
  await page.getByLabel("Service", { exact: true }).fill("payment-api");
  await page.getByLabel("Environment", { exact: true }).fill("production");
  await page
    .getByLabel("Technologies", { exact: true })
    .fill("postgresql, pgbouncer");
  await page
    .getByLabel("Search operational memory")
    .fill("HTTP 503 connection pool exhaustion");
  const request = page.waitForRequest("**/api/v1/evidence/retrieve");
  await page.getByRole("button", { name: "Search memory" }).click();
  expect((await request).postDataJSON()).toEqual({
    query: "HTTP 503 connection pool exhaustion",
    context: {
      service: "payment-api",
      environment: "production",
      technologies: ["postgresql", "pgbouncer"],
    },
    options: { top_k: 5 },
  });
  await expect(
    page.getByText("same technology: postgresql", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("matching HTTP 503 signal", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Scope expanded: service", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("UNVERIFIED", { exact: true })).toBeVisible();
});

test("degraded retrieval and failed remediation remain explicit negative evidence", async ({
  page,
}) => {
  await page.route("**/api/v1/evidence/retrieve", (route) =>
    route.fulfill({
      json: {
        status: "DEGRADED_RETRIEVAL",
        retrieval_stage: "GENERAL",
        retrieval_time_ms: 9,
        semantic_available: false,
        candidate_count: 1,
        stages_attempted: ["GENERAL"],
        warnings: ["semantic index unavailable; lexical fallback used"],
        results: [
          {
            id: "MEM-NEGATIVE-TEST",
            document_type: "incident",
            title: "Database restart failed",
            text: "The service remained degraded.",
            score: 0.7,
            tags: [],
            verification_outcome: "WORSE",
            historical_action: "restart_database",
            why_retrieved: ["same failure mode"],
          },
        ],
      },
    }),
  );
  await page.goto("/#/memory");
  await page
    .getByLabel("Search operational memory")
    .fill("Database saturation");
  await page.getByRole("button", { name: "Search memory" }).click();
  await expect(
    page.getByText("Degraded retrieval", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("semantic index unavailable; lexical fallback used", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText("WORSE", { exact: true })).toBeVisible();
  await expect(
    page.getByText(
      /Negative evidence: restart database did not establish recovery/,
    ),
  ).toBeVisible();
});

test("evaluation shows computed baselines without fabricating safety results", async ({
  page,
}) => {
  await page.goto("/#/evaluation");
  await page.getByRole("button", { name: "Run retrieval benchmark" }).click();
  const table = page.getByRole("table", {
    name: "Measured retrieval baselines",
  });
  await expect(table).toBeVisible();
  await expect(table.getByRole("row")).toHaveCount(3);
  await expect(
    table.getByRole("row").filter({ hasText: "vector only" }),
  ).toContainText("0.750");
  await expect(
    table.getByRole("row").filter({ hasText: "full" }),
  ).toContainText("0.8");
  await expect(page.getByText(/Safety evaluation: not measured/)).toBeVisible();
  await expect(page.getByText(/fixed examples/)).toHaveCount(0);
});

test("AI status distinguishes configured primary from actual heuristic fallback", async ({
  page,
}) => {
  await page.goto("/#/console");
  await expect(
    page.getByRole("heading", { name: "AI connection" }),
  ).toBeVisible();
  await expect(
    page.getByText("DEGRADED · HEURISTIC", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("heuristic-v1", { exact: true })).toBeVisible();
  await expect(
    page.getByText(/Local heuristic fallback is active/),
  ).toBeVisible();
});

test("console token is memory-only, used for requests, and removed on reload", async ({
  page,
}) => {
  const token = "TEST_CONSOLE_OPERATOR_TOKEN";
  const authorizations: (string | undefined)[] = [];
  await page.route("**/api/health", (route) => {
    authorizations.push(route.request().headers().authorization);
    return route.fulfill({ json: health });
  });
  await page.goto("/#/settings");
  await page.getByLabel("Console access token").fill(token);
  await page
    .getByRole("button", { name: "Save connection and reconnect" })
    .click();
  await expect(
    page.getByText("Access token held in memory", { exact: true }),
  ).toBeVisible();
  await expect.poll(() => authorizations.at(-1)).toBe(`Bearer ${token}`);
  await expect(page.getByLabel("Console access token")).toHaveValue("");
  expect(
    await page.evaluate(() =>
      JSON.stringify({
        local: { ...localStorage },
        session: { ...sessionStorage },
      }),
    ),
  ).not.toContain(token);
  await page.reload();
  await expect(
    page.getByText("No access token in memory", { exact: true }),
  ).toBeVisible();
  await expect.poll(() => authorizations.at(-1)).toBeUndefined();
});

test("changing backend clears console access before sending any new requests", async ({
  page,
}) => {
  await page.goto("/#/settings");
  await page
    .getByLabel("Console access token")
    .fill("TEST_CONSOLE_OPERATOR_TOKEN");
  await page
    .getByRole("button", { name: "Save connection and reconnect" })
    .click();
  await expect(
    page.getByText("Access token held in memory", { exact: true }),
  ).toBeVisible();
  const authorizations: (string | undefined)[] = [];
  await page.route("https://backend.example.test/api/health", (route) => {
    authorizations.push(route.request().headers().authorization);
    return route.fulfill({ json: health });
  });
  await page
    .getByLabel("Backend base URL")
    .fill("https://backend.example.test");
  await page
    .getByRole("button", { name: "Save connection and reconnect" })
    .click();
  await expect(
    page.getByText("No access token in memory", { exact: true }),
  ).toBeVisible();
  await expect.poll(() => authorizations.length).toBeGreaterThan(0);
  expect(authorizations.every((value) => value === undefined)).toBe(true);
});

test("private API reads explain missing console authorization", async ({
  page,
}) => {
  await page.route("**/api/**", (route) =>
    route.fulfill({ status: 401, json: { detail: "Authentication required" } }),
  );
  await page.goto("/#/memory");
  await expect(page.locator(".connection-banner")).toContainText(
    "Console access is required or has expired",
  );
  await expect(
    page
      .locator(".connection-banner")
      .getByRole("link", { name: "Connection settings" }),
  ).toBeVisible();
});
