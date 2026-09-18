import { test, expect } from "@playwright/test";
import { mockApi, approval, health } from "./fixtures";
const workspaceRoutes = [
  "console",
  "incidents",
  "topology",
  "events",
  "predictions",
  "simulator",
  "optimizer",
  "memory",
  "cortex",
  "approvals",
  "policies",
  "audit",
  "demo",
  "operations",
  "chaos",
  "reliability",
  "cost",
  "sustainability",
  "evaluation",
  "providers",
  "settings",
];
test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

for (const width of [390, 1440]) {
  test(`all routed workspaces have a readable light shell without viewport overflow at ${width}px`, async ({
    page,
  }) => {
    test.setTimeout(90000);
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (const route of workspaceRoutes) {
      await page.goto(`/#/${route}`);
      await expect(page.locator("main h1")).toBeVisible();
      await expect(page.getByText("This view could not render.")).toHaveCount(
        0,
      );
      await expect(page.getByText("Loading workspace…")).toHaveCount(0);
      await expect(page.getByText("Loading backend data…")).toHaveCount(0);
      const presentation = await page.getByRole("main").evaluate((main) => {
        const channels = (color: string) =>
          (color.match(/[\d.]+/g) || []).map(Number);
        const luminance = (color: number[]) => {
          const linear = color.slice(0, 3).map((channel) => {
            const value = channel / 255;
            return value <= 0.04045
              ? value / 12.92
              : ((value + 0.055) / 1.055) ** 2.4;
          });
          return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
        };
        let surface: Element | null = main;
        let background: number[] = [];
        while (surface) {
          const color = channels(getComputedStyle(surface).backgroundColor);
          if (color.length === 3 || (color.length === 4 && color[3] === 1)) {
            background = color;
            break;
          }
          surface = surface.parentElement;
        }
        const ink = channels(getComputedStyle(main.querySelector("h1")!).color);
        const backgroundLuminance = luminance(background);
        const inkLuminance = luminance(ink);
        const bounds = main.getBoundingClientRect();
        return {
          backgroundLuminance,
          headingContrast:
            (Math.max(backgroundLuminance, inkLuminance) + 0.05) /
            (Math.min(backgroundLuminance, inkLuminance) + 0.05),
          documentFits: document.documentElement.scrollWidth <= innerWidth + 1,
          mainFits: bounds.left >= -1 && bounds.right <= innerWidth + 1,
          // Table and graph wrappers can scroll; the workspace itself must fit.
          workspaceFits:
            !main.parentElement ||
            main.parentElement.scrollWidth <=
              main.parentElement.clientWidth + 1,
        };
      });
      const context = `${route} at ${width}px`;
      expect(presentation.backgroundLuminance, context).toBeGreaterThan(0.7);
      expect(presentation.headingContrast, context).toBeGreaterThanOrEqual(4.5);
      expect(presentation.documentFits, context).toBe(true);
      expect(presentation.mainFits, context).toBe(true);
      expect(presentation.workspaceFits, context).toBe(true);
    }
    expect(errors).toEqual([]);
  });
}
test("incident search and detail use persisted records", async ({ page }) => {
  await page.goto("/#/incidents");
  await page.getByLabel("Search incidents").fill("no-match");
  await expect(page.getByText("No matching incidents")).toBeVisible();
  await page.getByLabel("Search incidents").fill("checkout");
  await page.getByRole("button", { name: "INC-TEST-101" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Connection pool exhausted",
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
test("offline guard actions are disabled and no fabricated health is shown", async ({
  page,
}) => {
  await page.route("**/api/**", (r) =>
    r.fulfill({ status: 502, json: { error: "Test backend offline" } }),
  );
  await page.goto("/#/cortex");
  await expect(
    page.getByText("Backend unavailable.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Freeze mutations" }),
  ).toBeDisabled();
  await expect(page.getByText("99.96%")).toHaveCount(0);
});
test("guard mutation failures do not optimistically change confirmed state", async ({
  page,
}) => {
  await page.route("**/api/cortex/kill-switch", (r) =>
    r.fulfill({ status: 500, json: { detail: "Freeze rejected" } }),
  );
  await page.goto("/#/cortex");
  await page.getByRole("button", { name: "Freeze mutations" }).click();
  await expect(page.getByRole("alert")).toContainText("Freeze rejected");
  await expect(
    page.getByRole("button", { name: "Freeze mutations" }),
  ).toBeVisible();
  await expect(
    page.getByText("Backend confirmed: mutations frozen."),
  ).toHaveCount(0);
});
test("approval requires review and keeps server errors in the dialog", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/cortex/approvals/resolve", (r) => {
    calls++;
    return r.fulfill({
      json: { status: "expired", message: "Approval expired; re-evaluate." },
    });
  });
  await page.goto("/#/approvals");
  await page.getByRole("button", { name: "Review approval" }).click();
  expect(calls).toBe(0);
  await expect(
    page.getByRole("button", { name: "Approve and submit" }),
  ).toBeDisabled();
  await page.getByLabel("Operator name").fill("Test operator");
  await page.getByRole("button", { name: "Approve and submit" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Approval expired; re-evaluate.",
  );
  expect(calls).toBe(1);
});
test("expired approvals cannot be submitted", async ({ page }) => {
  await page.route("**/api/cortex/approvals", (r) =>
    r.fulfill({
      json: { pending_approvals: [{ ...approval, created_at: 1 }] },
    }),
  );
  await page.goto("/#/approvals");
  await expect(
    page.getByRole("button", { name: "Review approval" }),
  ).toBeDisabled();
  await expect(page.getByText("Re-evaluation required")).toBeVisible();
});
test("twin simulation precedes reviewed gateway execution and preserves blocked status", async ({
  page,
}) => {
  const mutations: unknown[] = [];
  page.on("request", (r) => {
    if (r.url().endsWith("/api/tools/action")) mutations.push(r.postDataJSON());
  });
  await page.goto("/#/simulator");
  await page
    .getByLabel("Target service", { exact: true })
    .selectOption("payment-api");
  await page.getByLabel("Target replicas").fill("9");
  await page.getByRole("button", { name: "Simulate change" }).click();
  await page.getByRole("button", { name: "Review execution" }).click();
  expect(mutations).toEqual([]);
  await page.getByRole("button", { name: "Submit through CORTEX" }).click();
  await expect(
    page.getByText("Blocked by test policy.", { exact: true }),
  ).toBeVisible();
  expect(mutations).toEqual([
    {
      action_type: "scale_service",
      params: { service: "payment-api", replicas: 9 },
      actor: "console-operator",
    },
  ]);
});
test("optimizer sends edited inputs and never executes infrastructure", async ({
  page,
}) => {
  let body: unknown;
  let mutations = 0;
  page.on("request", (r) => {
    if (r.url().endsWith("/api/optimizer")) body = r.postDataJSON();
    if (r.url().endsWith("/api/tools/action")) mutations++;
  });
  await page.goto("/#/cost");
  await page.getByLabel("Current replicas").fill("4");
  await page.getByLabel("Forecast demand (RPS)").fill("700");
  await page.getByRole("button", { name: "Compare configurations" }).click();
  await expect(
    page.getByText("Candidate comparison", { exact: true }),
  ).toBeVisible();
  expect(body).toEqual({
    mode: "COST",
    current_replicas: 4,
    forecast_rps: 700,
  });
  expect(mutations).toBe(0);
});
test("memory retrieves query and displays escaped source content", async ({
  page,
}) => {
  await page.goto("/#/memory");
  await page
    .getByLabel("Search operational memory")
    .fill("database connection pool");
  await page
    .getByRole("button", { name: "Search memory", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Connection pool recovery" }),
  ).toBeVisible();
  await expect(
    page.getByText("Review connection limits.", { exact: true }),
  ).toBeVisible();
});
test("pipeline renders actual outcome instead of interpreting HTTP success as recovery", async ({
  page,
}) => {
  await page.goto("/#/demo");
  await page
    .getByLabel("Observed symptom")
    .fill("Payment checkout latency is above the configured target.");
  await page.getByRole("button", { name: "Review control-loop run" }).click();
  await page.getByRole("button", { name: "Run reviewed incident" }).click();
  await expect(
    page.getByText("BLOCKED", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("Response received", { exact: true }),
  ).toHaveCount(9);
});
test("command search works with keyboard and restores focus", async ({
  page,
}) => {
  await page.goto("/#/console");
  await page.keyboard.press("Control+k");
  await page.getByLabel("Search workspaces").fill("digital");
  await page
    .getByRole("dialog")
    .getByRole("link", { name: "Digital twin" })
    .click();
  await expect(page).toHaveURL(/#\/simulator/);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
test("mobile navigation and layouts fit a narrow screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#/console");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page
    .getByRole("dialog")
    .getByRole("link", { name: "Predictions", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Predictions", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", {
      name: "Modeled historical requests and forecast with uncertainty bounds",
    }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "artifacts/mobile-predictions.png",
    fullPage: true,
  });
});
test("landing has functional entry points, reduced-motion support, and no mobile overflow", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your cloud, under control." }),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/landing-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("link", { name: "Launch command center" }).click();
  await expect(page).toHaveURL(/#\/console/);
});
test("landing directory exposes every console workspace with valid routes", async ({
  page,
}) => {
  await page.goto("/");
  const directory = page.getByRole("region", { name: /The whole picture/ });
  const links = directory.getByRole("link");
  await expect(links).toHaveCount(workspaceRoutes.length);
  const routes = await links.evaluateAll((items) =>
    items.map((item) => item.getAttribute("href")),
  );
  expect(routes.slice().sort()).toEqual(
    workspaceRoutes.map((route) => `#/${route}`).sort(),
  );
  for (const link of await links.all()) {
    await expect(link.getByRole("heading", { level: 3 })).not.toBeEmpty();
  }
  await directory.getByRole("link", { name: /Connection settings/ }).click();
  await expect(page).toHaveURL(/#\/settings/);
  await expect(
    page.getByRole("heading", { name: "Connection settings", exact: true }),
  ).toBeVisible();
});
test("landing mobile navigation opens, closes, and reaches an actual workspace", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const navigation = page.getByRole("navigation", { name: "Product" });
  const open = page.getByRole("button", { name: "Open product navigation" });
  await expect(open).toHaveAttribute("aria-expanded", "false");
  await expect(navigation).toBeHidden();
  await open.click();
  await expect(navigation).toBeVisible();
  const close = page.getByRole("button", { name: "Close product navigation" });
  await expect(close).toHaveAttribute("aria-expanded", "true");
  await close.click();
  await expect(navigation).toBeHidden();
  await open.click();
  await navigation
    .getByRole("link", { name: "Governance", exact: true })
    .click();
  await expect(page).toHaveURL(/#\/cortex/);
  await expect(
    page.getByRole("heading", { name: "CORTEX Guard", exact: true }),
  ).toBeVisible();
});
test("control-loop phases change the explanation and destination without an API action", async ({
  page,
}) => {
  const mutations: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().includes("/api/"))
      mutations.push(request.url());
  });
  await page.goto("/");
  const process = page.getByRole("region", { name: "The control loop" });
  for (const phase of [
    {
      button: "Simulate & optimize",
      heading: "Explore the consequences first.",
      link: "Open the digital twin",
      route: "simulator",
    },
    {
      button: "Authorize & act",
      heading: "Make authority explicit.",
      link: "Review CORTEX Guard",
      route: "cortex",
    },
    {
      button: "Verify & learn",
      heading: "Keep the evidence close.",
      link: "Inspect the evidence ledger",
      route: "audit",
    },
    {
      button: "Observe & predict",
      heading: "Start with a clearer picture.",
      link: "Explore infrastructure",
      route: "topology",
    },
  ]) {
    const button = process.getByRole("button", {
      name: new RegExp(phase.button),
    });
    await button.click();
    await expect(button).toHaveAttribute("aria-pressed", "true");
    await expect(process.getByRole("button", { pressed: true })).toHaveCount(1);
    await expect(
      process.getByRole("heading", { name: phase.heading }),
    ).toBeVisible();
    await expect(
      process.getByRole("link", { name: phase.link }),
    ).toHaveAttribute("href", `#/${phase.route}`);
  }
  expect(mutations).toEqual([]);
});
test("landing scroll condenses navigation and advances the metallic story", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/");
  await expect(page.locator(".br-page")).toHaveAttribute(
    "data-motion-enabled",
    "true",
  );
  await expect(page.locator("html")).toHaveClass(/\blenis\b/);
  await page.evaluate(() => document.fonts.ready);
  const navigation = page.locator(".br-nav");
  const stage = page.locator(".br-stage");
  await expect(navigation).toHaveAttribute("data-condensed", "false");
  const range = await stage.evaluate((element) => ({
    start: element.getBoundingClientRect().top + scrollY,
    distance: element.getBoundingClientRect().height - innerHeight,
  }));
  expect(range.distance).toBeGreaterThan(0);
  await page.evaluate(
    (top) => window.scrollTo({ top, behavior: "instant" }),
    range.start + range.distance * 0.2,
  );
  await expect(navigation).toHaveAttribute("data-condensed", "true");
  await expect
    .poll(async () => Number(await stage.getAttribute("data-motion-progress")))
    .toBeCloseTo(0.2, 1);
  const earlierTransform = await page
    .locator(".br-metal-left")
    .evaluate((element) => getComputedStyle(element).transform);
  await page.evaluate(
    (top) => window.scrollTo({ top, behavior: "instant" }),
    range.start + range.distance * 0.8,
  );
  await expect
    .poll(async () => Number(await stage.getAttribute("data-motion-progress")))
    .toBeCloseTo(0.8, 1);
  await expect
    .poll(() =>
      page
        .locator(".br-metal-left")
        .evaluate((element) => getComputedStyle(element).transform),
    )
    .not.toBe(earlierTransform);
  const progress = Number(await stage.getAttribute("data-motion-progress"));
  expect(progress).toBeGreaterThanOrEqual(0);
  expect(progress).toBeLessThanOrEqual(1);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await expect(navigation).toHaveAttribute("data-condensed", "false");
});
test("desktop sticky process advances all four phases and keeps keyboard selection", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveClass(/\blenis\b/);
  await page.evaluate(() => document.fonts.ready);
  const process = page.getByRole("region", { name: "The control loop" });
  const sticky = process.locator(".br-process-sticky");
  await expect(sticky).toHaveCSS("position", "sticky");
  const range = await process.evaluate((element) => ({
    start: element.getBoundingClientRect().top + scrollY,
    distance: element.getBoundingClientRect().height - innerHeight,
  }));
  expect(range.distance).toBeGreaterThan(0);
  const phases = [
    "Observe & predict",
    "Simulate & optimize",
    "Authorize & act",
    "Verify & learn",
  ];
  for (let index = 0; index < phases.length; index++) {
    await page.evaluate(
      (top) => window.scrollTo({ top, behavior: "instant" }),
      range.start + range.distance * ((index + 0.5) / phases.length),
    );
    await expect(
      process.getByRole("button", { name: new RegExp(phases[index]) }),
    ).toHaveAttribute("aria-pressed", "true");
    await expect(process.getByRole("button", { pressed: true })).toHaveCount(1);
    const bounds = await sticky.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.y).toBeGreaterThanOrEqual(-1);
    expect(bounds!.y).toBeLessThan(150);
  }
  const first = process.getByRole("button", { name: /Observe & predict/ });
  await first.focus();
  await page.keyboard.press("Space");
  await expect(first).toHaveAttribute("aria-pressed", "true");
  await expect(
    process.getByRole("heading", { name: "Start with a clearer picture." }),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    process.getByRole("link", { name: "Explore infrastructure" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  const second = process.getByRole("button", { name: /Simulate & optimize/ });
  await expect(second).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(second).toHaveAttribute("aria-pressed", "true");
  await expect(
    process.getByRole("link", { name: "Open the digital twin" }),
  ).toHaveAttribute("href", "#/simulator");
});
test("motion can be paused, persists across reload, and resumes without duplicate controls", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveClass(/\blenis\b/);
  await page.getByRole("button", { name: "Pause motion", exact: true }).click();
  await expect(page.locator(".br-page")).toHaveAttribute(
    "data-motion-enabled",
    "false",
  );
  await expect(page.locator("html")).not.toHaveClass(/\blenis\b/);
  await expect(page.locator("html")).toHaveAttribute("data-motion", "off");
  await expect(page.locator(".br-stage")).toHaveAttribute(
    "data-motion-progress",
    "1",
  );
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Enable motion", exact: true }),
  ).toBeVisible();
  await expect(page.locator("html")).not.toHaveClass(/\blenis\b/);
  const stage = page.locator(".br-stage");
  const stageTop = await stage.evaluate(
    (element) => element.getBoundingClientRect().top + scrollY,
  );
  await page.evaluate(
    (top) => window.scrollTo({ top, behavior: "instant" }),
    stageTop + 100,
  );
  await expect(stage).toHaveAttribute("data-motion-progress", "1");
  await page
    .getByRole("button", { name: "Enable motion", exact: true })
    .click();
  await expect(page.locator(".br-page")).toHaveAttribute(
    "data-motion-enabled",
    "true",
  );
  await expect(page.locator("html")).toHaveClass(/\blenis\b/);
  await expect(
    page.getByRole("button", { name: "Pause motion", exact: true }),
  ).toHaveCount(1);
  await page.getByRole("button", { name: "Pause motion", exact: true }).click();
  await expect(page.locator("html")).not.toHaveClass(/\blenis\b/);
});
test("system reduced motion skips smooth scrolling and timeline transforms while preserving content", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator(".br-page")).toHaveAttribute(
    "data-motion-enabled",
    "false",
  );
  await expect(page.locator("html")).toHaveAttribute("data-motion", "off");
  await expect(page.locator("html")).not.toHaveClass(/\blenis\b/);
  await expect(
    page.getByRole("button", { name: "Motion reduced by system preference" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("heading", { name: "Your cloud, under control." }),
  ).toBeVisible();
  const stage = page.locator(".br-stage");
  await expect(stage).toHaveAttribute("data-motion-progress", "1");
  const transforms = await page
    .locator(".br-hero-line > span, .br-metal-left, .br-metal-right, .br-story")
    .evaluateAll((elements) =>
      elements.map((element) => (element as HTMLElement).style.transform),
    );
  expect(transforms.every((transform) => transform === "")).toBe(true);
  const story = page.locator(".br-story");
  await story.scrollIntoViewIfNeeded();
  await expect(story).toHaveCSS("opacity", "1");
  await expect(page.locator("html")).not.toHaveClass(/\blenis\b/);
  await expect(stage).toHaveAttribute("data-motion-progress", "1");
  const process = page.getByRole("region", { name: "The control loop" });
  await process.getByRole("button", { name: /Verify & learn/ }).click();
  await expect(
    process.getByRole("heading", { name: "Keep the evidence close." }),
  ).toBeVisible();
  await expect(
    process.getByRole("link", { name: "Inspect the evidence ledger" }),
  ).toHaveAttribute("href", "#/audit");
});
test("provider placeholders cannot claim a connection", async ({ page }) => {
  await page.goto("/#/providers");
  await expect(page.getByText("Not implemented", { exact: true })).toHaveCount(
    4,
  );
  await expect(page.getByText("Runtime unknown", { exact: true })).toHaveCount(
    2,
  );
});
test("failed refresh preserves the last snapshot with a stale warning", async ({
  page,
}) => {
  await page.goto("/#/incidents");
  await expect(page.getByText("INC-TEST-101")).toBeVisible();
  await page.route("**/api/incidents", (r) =>
    r.fulfill({ status: 503, json: { detail: "Temporarily unavailable" } }),
  );
  await page.getByRole("button", { name: "Refresh data" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Showing the last snapshot",
  );
  await expect(page.getByText("INC-TEST-101")).toBeVisible();
});
test("connection rejects credential-bearing URLs", async ({ page }) => {
  await page.goto("/#/settings");
  await page
    .getByLabel("Backend base URL")
    .fill("https://user:password@example.com");
  await page
    .getByRole("button", { name: "Save connection and reconnect" })
    .click();
  await expect(page.getByRole("alert")).toContainText("without credentials");
});
test("dashboard screenshot records fixture data without injecting it into production", async ({
  page,
}) => {
  await page.goto("/#/console");
  await expect(
    page.getByRole("button", { name: "Inspect payment-api" }),
  ).toBeVisible();
  await expect(
    page.getByText("Checkout latency above threshold"),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/console-fixture-desktop.png",
    fullPage: true,
  });
});

test("operator notes use the event API and clearing requires explicit confirmation", async ({
  page,
}) => {
  let notePayload: unknown;
  let clears = 0;
  await page.route("**/api/events/emit", async (route) => {
    notePayload = route.request().postDataJSON();
    await route.fulfill({ json: { status: "success" } });
  });
  await page.route("**/api/events/clear", async (route) => {
    clears++;
    await route.fulfill({
      status: 503,
      json: { detail: "Timeline storage unavailable" },
    });
  });
  await page.goto("/#/events");
  await page.getByLabel("Operator note").fill("Checking payment latency");
  await page.getByRole("button", { name: "Add note" }).click();
  await expect(
    page.getByText("Note added to the activity stream."),
  ).toBeVisible();
  expect(notePayload).toEqual({
    type: "operator_note",
    payload: { message: "Checking payment latency", source: "console" },
  });
  await page.getByText("Activity stream maintenance").click();
  await page
    .getByRole("button", { name: "Clear activity stream", exact: true })
    .click();
  expect(clears).toBe(0);
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  expect(clears).toBe(0);
  await page
    .getByRole("button", { name: "Clear activity stream", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm clear" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Timeline storage unavailable",
  );
  expect(clears).toBe(1);
  await expect(
    page.getByText("Activity stream cleared.", { exact: true }),
  ).toHaveCount(0);
});
