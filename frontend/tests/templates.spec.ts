import { expect, test, type Page } from "@playwright/test";
import type { components } from "../src/lib/api/schema";

const pattern =
    "Dear customer,\nYour account <*> was debited by INR <*> at <*>.\nAvailable balance: INR <*>.";
const template: components["schemas"]["TemplateResponse"] = {
    id: 7,
    text: pattern,
    email_count: 51,
    account_id: null,
};
const email: components["schemas"]["EmailDetail"] = {
    id: 12,
    message_id: "gmail-12",
    sender: "Alerts <alerts@example.com>",
    subject: "Your account activity",
    received_at: "2026-09-01T09:30:00Z",
    template_id: 7,
    representation: null,
    body: "Dear customer,\nYour account 1234 was debited by INR 420.00 at Corner Store.\nAvailable balance: INR 8,500.00.",
};
const paginated = <T>(items: T[], page = 1, total = 51) => ({
    items,
    page,
    total,
    page_size: 50,
    total_pages: Math.ceil(total / 50),
});

async function mockWorkspace(page: Page) {
    await page.route(
        (url) => url.pathname.startsWith("/api/"),
        async (route) => {
            const url = new URL(route.request().url());
            const current = Number(url.searchParams.get("page") ?? 1);
            switch (url.pathname) {
                case "/api/templates":
                    return route.fulfill({
                        json: paginated(current > 2 ? [] : [template], current),
                    });
                case "/api/templates/7":
                    return route.fulfill({ json: { ...template, example: email } });
                case "/api/emails":
                    return route.fulfill({ json: paginated(current > 2 ? [] : [email], current) });
                case "/api/emails/12":
                    return route.fulfill({ json: email });
                default:
                    return route.fulfill({ status: 404, json: { detail: "Not found" } });
            }
        },
    );
}

test.beforeEach(async ({ page }) => {
    await mockWorkspace(page);
});

test("extracts once, shows exact counts, resets pagination and refreshes email assignments", async ({
    page,
}) => {
    let extracted = false;
    let calls = 0;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
        release = resolve;
    });
    await page.route("**/api/emails/12", (route) =>
        route.fulfill({
            json: { ...email, template_id: extracted ? 7 : null },
        }),
    );
    await page.route("**/api/templates?*", (route) =>
        route.fulfill({
            json: paginated(
                [{ ...template, email_count: extracted ? 53 : 51 }],
                Number(new URL(route.request().url()).searchParams.get("page")),
            ),
        }),
    );
    await page.route("**/api/email-template-assignment", async (route) => {
        calls++;
        expect(route.request().method()).toBe("POST");
        expect(route.request().postData()).toBeNull();
        await gate;
        extracted = true;
        await route.fulfill({ json: { processed: 4, skipped: 2, templates_created: 1 } });
    });
    await page.goto("/emails/12");
    await expect(page.getByText("No template assigned")).toBeVisible();
    await page
        .getByRole("navigation", { name: "Main navigation" })
        .getByRole("link", { name: "Templates" })
        .click();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page).toHaveURL("/templates?page=2");
    await page.getByRole("button", { name: "Extract templates", exact: true }).dblclick();
    await expect(page.getByRole("button", { name: "Extracting…" })).toBeDisabled();
    await expect(page.getByRole("status")).toContainText("Finding patterns");
    expect(calls).toBe(1);
    release();
    await expect(page.getByRole("status")).toContainText(
        "4 processed · 2 skipped · 1 templates created",
    );
    await expect(page.getByRole("status")).toContainText("empty or whitespace-only bodies");
    await expect(page).toHaveURL("/templates?page=1");
    await expect(page.getByText("53 emails", { exact: true })).toBeVisible();
    await page
        .getByRole("navigation", { name: "Main navigation" })
        .getByRole("link", { name: "Emails", exact: true })
        .click();
    await page.getByRole("link", { name: /Your account activity/ }).click();
    await expect(page.getByRole("link", { name: "Template 7", exact: true })).toBeVisible();
    expect(calls).toBe(1);
});

test("extraction failure supports manual retry and an empty run", async ({ page }) => {
    let calls = 0;
    await page.route("**/api/templates?*", (route) => route.fulfill({ json: paginated([], 1, 0) }));
    await page.route("**/api/email-template-assignment", (route) => {
        calls++;
        return route.fulfill(
            calls === 1
                ? { status: 503, json: { detail: "Extraction is unavailable. Try again." } }
                : { json: { processed: 0, skipped: 0, templates_created: 0 } },
        );
    });
    await page.goto("/templates");
    await expect(page.getByRole("heading", { name: "No templates yet" })).toBeVisible();
    await page.getByRole("button", { name: "Extract templates", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText("Extraction is unavailable");
    expect(calls).toBe(1);
    await page.getByRole("button", { name: "Extract templates", exact: true }).click();
    await expect(page.getByRole("status")).toContainText(
        "0 processed · 0 skipped · 0 templates created",
    );
    expect(calls).toBe(2);
});

test("successful extraction remains visible when the list refresh fails", async ({ page }) => {
    let extracted = false;
    await page.route("**/api/templates?*", (route) =>
        route.fulfill(
            extracted
                ? { status: 503, json: { detail: "Templates could not be loaded" } }
                : { json: paginated([template]) },
        ),
    );
    await page.route("**/api/email-template-assignment", (route) => {
        extracted = true;
        return route.fulfill({ json: { processed: 2, skipped: 0, templates_created: 1 } });
    });
    await page.goto("/templates");
    await expect(page.getByRole("link", { name: /Template 7/ })).toBeVisible();
    await page.getByRole("button", { name: "Extract templates", exact: true }).click();
    await expect(page.getByRole("status")).toContainText("Extraction complete.");
    await expect(page.getByRole("alert")).toContainText("Templates could not be loaded");
    await page.route("**/api/templates?*", (route) =>
        route.fulfill({ json: paginated([template]) }),
    );
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(page.getByRole("status")).toContainText("2 processed");
});

test("template and matching-email pagination survive detail navigation and reload", async ({
    page,
}, testInfo) => {
    const filters: string[] = [];
    await page.route("**/api/emails?*", (route) => {
        const url = new URL(route.request().url());
        filters.push(url.searchParams.get("template_id") ?? "missing");
        return route.fulfill({ json: paginated([email], Number(url.searchParams.get("page"))) });
    });
    await page.goto("/templates?page=2");
    await expect(page.getByRole("link", { name: "Templates", exact: true })).toHaveAttribute(
        "aria-current",
        "page",
    );
    await expect(page).toHaveTitle("Templates · Aggregator");
    await page.screenshot({ path: testInfo.outputPath("templates.png"), fullPage: true });
    await page.getByRole("link", { name: /Template 7/ }).click();
    await expect(page).toHaveURL("/templates/7?page=2&emailsPage=1");
    await expect(page).toHaveTitle("Template detail · Aggregator");
    await expect(page.locator("#main")).toBeFocused();
    await expect(page.getByRole("region", { name: "Template pattern" })).toContainText(pattern);
    await expect(page.getByRole("region", { name: "Example email" })).toContainText(email.body);
    await expect(page.getByRole("navigation", { name: "Matching email pages" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("template-detail.png"), fullPage: true });
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page).toHaveURL("/templates/7?page=2&emailsPage=2");
    await page
        .getByRole("region", { name: "Matching emails" })
        .getByRole("link", { name: /Your account activity/ })
        .click();
    await expect(page).toHaveURL("/emails/12?fromTemplate=7&templatePage=2&emailsPage=2");
    await page.reload();
    await page.getByRole("link", { name: "Back to template", exact: true }).click();
    await expect(page).toHaveURL("/templates/7?page=2&emailsPage=2");
    await expect(page.getByText("Page 2 of 2")).toBeVisible();
    expect(filters.every((filter) => filter === "7")).toBe(true);
    await page.getByRole("link", { name: "Back to templates", exact: true }).click();
    await expect(page).toHaveURL("/templates?page=2");
});

test("loading, failed read, retry and out-of-range template pages", async ({ page }) => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
        release = resolve;
    });
    await page.route("**/api/templates?*", async (route) => {
        await gate;
        await route.abort();
    });
    await page.goto("/templates?page=invalid");
    await expect(page.getByRole("status")).toHaveText("Loading templates…");
    release();
    await expect(page.getByRole("alert")).toContainText("Could not reach the Aggregator API");
    await page.unroute("**/api/templates?*");
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByText("Page 1 of 2")).toBeVisible();
    await page.goto("/templates?page=9");
    await expect(page.getByRole("heading", { name: "No templates on this page" })).toBeVisible();
    await page.getByRole("link", { name: "Go to first page" }).click();
    await expect(page).toHaveURL("/templates?page=1");
});

test("detail read failure, retry, missing example and missing template", async ({ page }) => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
        release = resolve;
    });
    await page.route("**/api/templates/7", async (route) => {
        await gate;
        await route.fulfill({ status: 500, body: "Internal Server Error" });
    });
    await page.goto("/templates/7");
    await expect(page.getByRole("status")).toHaveText("Loading template…");
    release();
    await expect(page.getByRole("alert")).toBeVisible();
    await page.route("**/api/templates/7", (route) =>
        route.fulfill({ json: { ...template, email_count: 0, example: null } }),
    );
    await page.route("**/api/emails?*", (route) => route.fulfill({ json: paginated([], 1, 0) }));
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByText("No example email is available for this template.")).toBeVisible();
    await expect(page.getByRole("heading", { name: "No matching emails" })).toBeVisible();
    await page.goto("/templates/999");
    await expect(page.getByRole("heading", { name: "Template not found" })).toBeVisible();
    await page.goto("/templates/invalid");
    await expect(page.getByRole("heading", { name: "Template not found" })).toBeVisible();
});

test("matching email loading, error and pagination recovery leave the pattern available", async ({
    page,
}) => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
        release = resolve;
    });
    await page.route("**/api/emails?*", async (route) => {
        await gate;
        await route.fulfill({ status: 503, json: { detail: "Matching emails unavailable" } });
    });
    await page.goto("/templates/7?page=2&emailsPage=9");
    await expect(page.getByRole("status")).toHaveText("Loading matching emails…");
    release();
    await expect(page.getByRole("alert")).toContainText("Matching emails unavailable");
    await expect(page.getByRole("heading", { name: "Template pattern" })).toBeVisible();
    await page.unroute("**/api/emails?*");
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByRole("heading", { name: "No emails on this page" })).toBeVisible();
    await page.getByRole("link", { name: "Go to first page" }).click();
    await expect(page).toHaveURL("/templates/7?page=2&emailsPage=1");
});

test("long patterns and email bodies are inert text and fit the viewport", async ({ page }) => {
    const unsafe = '<img src=x onerror="alert(1)">\n' + "long".repeat(150);
    await page.route("**/api/templates?*", (route) =>
        route.fulfill({ json: paginated([{ ...template, text: unsafe }]) }),
    );
    await page.route("**/api/templates/7", (route) =>
        route.fulfill({ json: { ...template, text: unsafe, example: { ...email, body: unsafe } } }),
    );
    await page.goto("/templates");
    await expect(page.locator(".template-preview")).toHaveText(unsafe);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
    );
    await page.getByRole("link", { name: /Template 7/ }).click();
    await expect(page.locator(".template-pattern")).toHaveText(unsafe);
    await expect(page.locator(".template-example .email-body")).toHaveText(unsafe);
    await expect(page.locator("main img")).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
    );
    await page.setViewportSize({ width: 320, height: 740 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
    );
});

test("email return links reject invalid origins and normalize pagination", async ({ page }) => {
    await page.goto("/emails/12?fromTemplate=https://example.com&templatePage=2&emailsPage=2");
    await expect(page.getByRole("link", { name: "Back to emails" })).toHaveAttribute(
        "href",
        "/emails?page=1",
    );
    await expect(page.getByRole("link", { name: "Template 7", exact: true })).toHaveAttribute(
        "href",
        "/templates/7",
    );
    await page.goto("/emails/12?fromTemplate=7&templatePage=-2&emailsPage=invalid");
    await expect(page.getByRole("link", { name: "Back to template", exact: true })).toHaveAttribute(
        "href",
        "/templates/7?page=1&emailsPage=1",
    );
});

test("navigating during extraction does not redirect and prevents a second run", async ({
    page,
}) => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
        release = resolve;
    });
    let calls = 0;
    await page.route("**/api/email-template-assignment", async (route) => {
        calls++;
        await gate;
        await route.fulfill({ json: { processed: 1, skipped: 0, templates_created: 0 } });
    });
    await page.goto("/templates?page=2");
    await page.getByRole("button", { name: "Extract templates", exact: true }).click();
    await page
        .getByRole("navigation", { name: "Main navigation" })
        .getByRole("link", { name: "Emails", exact: true })
        .click();
    await page
        .getByRole("navigation", { name: "Main navigation" })
        .getByRole("link", { name: "Templates", exact: true })
        .click();
    await expect(page.getByRole("button", { name: "Extracting…" })).toBeDisabled();
    release();
    await expect(
        page.getByRole("button", { name: "Extract templates", exact: true }),
    ).toBeEnabled();
    await expect(page).toHaveURL("/templates");
    expect(calls).toBe(1);
});
