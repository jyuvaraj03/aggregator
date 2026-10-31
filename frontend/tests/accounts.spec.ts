import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import type { Account } from "../src/api";

async function mockApi(page: Page, initial: Account[] = []) {
  const accounts = initial.map((account) => ({ ...account }));
  const calls: {
    path: string;
    method: string;
    body: Record<string, unknown> | null;
  }[] = [];
  let nextId = Math.max(0, ...accounts.map((account) => account.id)) + 1;
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace("/api", "");
    const method = request.method();
    const body = request.postDataJSON();
    calls.push({ path, method, body });
    let data: unknown;
    if (path === "/email-sync") data = { job_id: "sync" };
    else if (path === "/jobs/sync")
      data = {
        job_id: "sync",
        status: "succeeded",
        result: { template_assignment_job_id: "assign" },
      };
    else if (path === "/jobs/assign")
      data = {
        job_id: "assign",
        status: "succeeded",
        result: { templates_created: 0, template_classification_jobs: [] },
      };
    else if (path === "/accounts" && method === "GET")
      data = { items: [...accounts].reverse(), total_pages: 1 };
    else if (path === "/accounts" && method === "POST") {
      data = { id: nextId++, name: body.name, color: body.color };
      accounts.push(data as Account);
    } else if (/^\/accounts\/\d+$/.test(path)) {
      const id = Number(path.split("/").pop());
      const index = accounts.findIndex((account) => account.id === id);
      if (method === "PATCH") {
        accounts[index] = { ...accounts[index], ...body };
        data = accounts[index];
      } else if (method === "DELETE") {
        accounts.splice(index, 1);
        await route.fulfill({ status: 204 });
        return;
      }
    }
    if (data === undefined) {
      await route.fulfill({
        status: 404,
        json: { detail: `Unexpected ${method} ${path}` },
      });
      return;
    }
    await route.fulfill({ json: data });
  });
  return { accounts, calls };
}
async function setup(page: Page) {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Add your accounts" }),
  ).toBeVisible();
  await expect(page.getByLabel("Account name", { exact: true })).toBeVisible();
}

test("creates, edits, validates duplicates, and removes persisted accounts", async ({
  page,
}) => {
  const { accounts } = await mockApi(page);
  await setup(page);
  const name = page.getByLabel("Account name", { exact: true });
  await name.fill("Travel");
  await page.getByRole("button", { name: "Choose a theme colour" }).click();
  await page.getByRole("button", { name: "Violet", exact: true }).click();
  await name.press("Enter");
  await expect(
    page.getByRole("button", { name: "Edit Travel", exact: true }),
  ).toBeVisible();
  expect(accounts[0]).toMatchObject({ name: "Travel", color: 3 });
  await expect(name).toBeFocused();
  await name.fill("travel");
  await name.press("Enter");
  await expect(page.getByRole("alert")).toHaveText("Travel already exists");
  await page.getByRole("button", { name: "Edit Travel", exact: true }).click();
  await expect(name).toHaveValue("Travel");
  expect(
    await name.evaluate((input: HTMLInputElement) => [
      input.selectionStart,
      input.selectionEnd,
    ]),
  ).toEqual([6, 6]);
  await name.fill("Trips");
  await name.press("Enter");
  await page.getByRole("button", { name: "Edit Trips", exact: true }).click();
  await page.getByRole("button", { name: "Remove account" }).click();
  await expect(
    page.getByRole("button", { name: "Edit Trips", exact: true }),
  ).toHaveCount(0);
  expect(accounts).toHaveLength(0);
});

test("preserves the editor after save and removal failures", async ({
  page,
}) => {
  await mockApi(page, [{ id: 1, name: "Checking", color: 2 }]);
  await page.route("**/api/accounts/1", (route) =>
    route.fulfill({
      status: 409,
      json: { detail: "This account has saved transactions." },
    }),
  );
  await setup(page);
  await page
    .getByRole("button", { name: "Edit Checking", exact: true })
    .click();
  await page.getByRole("button", { name: "Remove account" }).click();
  await expect(page.getByRole("alert")).toContainText("saved transactions");
  await page.getByLabel("Account name", { exact: true }).fill("New name");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel("Account name", { exact: true })).toHaveValue(
    "New name",
  );
  await expect(
    page.getByRole("button", { name: "Edit Checking", exact: true }),
  ).toBeVisible();
});

test("supports keyboard colour selection, counters, Escape and dark mode persistence", async ({
  page,
}) => {
  await mockApi(page, [{ id: 1, name: "Checking", color: 0 }]);
  await setup(page);
  await page.getByRole("button", { name: "Choose a theme colour" }).click();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "Choose a theme colour, Indigo" }),
  ).toBeVisible();
  const name = page.getByLabel("Account name", { exact: true });
  await name.fill("A".repeat(40));
  await expect(page.getByText("40/40")).toBeVisible();
  await page
    .getByRole("button", { name: "Edit Checking", exact: true })
    .click();
  await page.keyboard.press("Escape");
  await expect(name).toHaveValue("");
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("submits sync once, resumes after reload and reaches the empty handoff", async ({
  page,
}) => {
  const { calls } = await mockApi(page);
  await setup(page);
  await expect(
    page.getByRole("button", { name: "See templates" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "See templates" }),
  ).toBeVisible();
  expect(calls.filter((call) => call.path === "/email-sync")).toHaveLength(1);
  await page.keyboard.press("Control+Enter");
  await expect(
    page.getByRole("heading", { name: "Template review is coming next" }),
  ).toBeVisible();
  await expect(
    page.getByText("No new email templates were found in this sync."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Back to accounts" }).click();
  await expect(page.getByLabel("Account name", { exact: true })).toBeVisible();
});

test("waits for downstream jobs and recovers a polling failure", async ({
  page,
}) => {
  await mockApi(page);
  let attempts = 0;
  let finished = false;
  await page.route("**/api/jobs/assign", async (route) => {
    attempts++;
    if (attempts === 1) {
      await route.fulfill({
        status: 503,
        json: { detail: "Status temporarily unavailable" },
      });
      return;
    }
    await route.fulfill({
      json: {
        job_id: "assign",
        status: finished ? "succeeded" : "running",
        result: finished
          ? { templates_created: 0, template_classification_jobs: [] }
          : null,
      },
    });
  });
  await setup(page);
  await expect(page.getByText("Status temporarily unavailable")).toBeVisible();
  await page.getByRole("button", { name: "Retry checking" }).click();
  await expect(
    page.getByRole("heading", { name: "Finding email templates…" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "See templates" })).toHaveCount(
    0,
  );
  finished = true;
  await expect(
    page.getByRole("button", { name: "See templates" }),
  ).toBeVisible();
});

test("restarts a failed chain with its original start date", async ({
  page,
}) => {
  const { calls } = await mockApi(page);
  await page.route("**/api/jobs/assign", (route) =>
    route.fulfill({
      json: { job_id: "assign", status: "failed", result: null },
    }),
  );
  await setup(page);
  await page.getByRole("button", { name: "Restart sync" }).click();
  await expect
    .poll(() => calls.filter((call) => call.path === "/email-sync").length)
    .toBe(2);
  const submissions = calls.filter((call) => call.path === "/email-sync");
  expect(submissions[0].body).toEqual(submissions[1].body);
});

test("captures desktop and mobile in both themes against the supplied reference", async ({
  page,
}) => {
  await mockApi(page, [
    { id: 1, name: "Everyday account", color: 0 },
    { id: 2, name: "Travel card", color: 3 },
    { id: 3, name: "Savings", color: 13 },
  ]);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await setup(page);
  await page.getByLabel("Account name", { exact: true }).fill("My new account");
  await page.screenshot({
    path: "../.impeccable/review/desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await page.screenshot({
    path: "../.impeccable/review/desktop-dark.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "../.impeccable/review/mobile-dark.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  await page.screenshot({
    path: "../.impeccable/review/mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const reference = await readFile(
    "../docs/frontend-reference/Template Review — mockup.html",
    "utf8",
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.setContent(reference);
  await expect(page.locator("#setup")).toBeVisible({ timeout: 10000 });
  await page.screenshot({
    path: "../.impeccable/review/reference-desktop.png",
    fullPage: true,
  });
});

test("keeps a large account collection reachable on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(
    page,
    Array.from({ length: 35 }, (_, i) => ({
      id: i + 1,
      name: `Account ${i + 1}`,
      color: i % 20,
    })),
  );
  await setup(page);
  await page
    .getByRole("button", { name: "Edit Account 35", exact: true })
    .click();
  await expect(page.getByLabel("Account name", { exact: true })).toHaveValue(
    "Account 35",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("runs the sync glide and account flight/removal with motion enabled", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.setViewportSize({ width: 1280, height: 800 });
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await mockApi(page);
  await page.goto("/");
  await expect(page.locator(".phase-center")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Syncing emails…" }),
  ).toBeVisible();
  await expect(page.locator(".phase-glide")).toBeVisible();
  await expect(page.getByLabel("Account name", { exact: true })).toBeVisible();
  await page
    .getByLabel("Account name", { exact: true })
    .fill("Animated account");
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "Edit Animated account", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Edit Animated account", exact: true })
    .click();
  await page.keyboard.press("Control+/");
  await expect(
    page.getByRole("button", { name: "Edit Animated account", exact: true }),
  ).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("keeps ready, editing, and failed sync actions below the editor on short desktops", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 600 });
  await mockApi(page, [{ id: 1, name: "Checking", color: 0 }]);
  await setup(page);
  async function assertNoOverlap() {
    const editor = await page.locator(".editor").boundingBox();
    const status = await page.locator(".sync-status").boundingBox();
    expect(editor).not.toBeNull();
    expect(status).not.toBeNull();
    expect(status!.y).toBeGreaterThanOrEqual(editor!.y + editor!.height + 24);
  }
  await expect(
    page.getByRole("button", { name: "See templates" }),
  ).toBeVisible();
  await assertNoOverlap();
  await page.screenshot({
    path: "../.impeccable/review/short-desktop-ready.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Edit Checking", exact: true })
    .click();
  await assertNoOverlap();
  await page.screenshot({
    path: "../.impeccable/review/short-desktop-editing.png",
    fullPage: true,
  });
  await page.route("**/api/jobs/assign", (route) =>
    route.fulfill({
      json: { job_id: "assign", status: "failed", result: null },
    }),
  );
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Restart sync" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Edit Checking", exact: true })
    .click();
  await assertNoOverlap();
  await page.screenshot({
    path: "../.impeccable/review/short-desktop-error.png",
    fullPage: true,
  });
});
