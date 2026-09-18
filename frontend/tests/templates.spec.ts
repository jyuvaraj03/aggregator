import { expect, test, type Page } from "@playwright/test";
import type { components } from "../src/lib/api/schema";

const pattern =
    "Dear customer,\nYour account <*> was debited by INR <*> at <*>.\nAvailable balance: INR <*>.";
const template: components["schemas"]["TemplateResponse"] = {
    id: 7,
    text: pattern,
    is_transaction_alert: null,
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

test("empty state explains that syncing creates templates automatically", async ({ page }) => {
    await page.route("**/api/templates?*", (route) => route.fulfill({ json: paginated([], 1, 0) }));
    await page.goto("/templates");
    await expect(page.getByRole("heading", { name: "No templates yet" })).toBeVisible();
    await expect(
        page.getByText("Sync your emails to create templates automatically."),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "Sync emails" })).toHaveAttribute(
        "href",
        "/emails",
    );
    await expect(page.getByRole("button", { name: /Extract templates/ })).toHaveCount(0);
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
