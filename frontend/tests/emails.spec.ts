import { expect, test, type Page } from "@playwright/test";
import type { components } from "../src/lib/api/schema";

type Summary = components["schemas"]["EmailSummary"];
const message: Summary = {
    id: 1,
    message_id: "gmail-1",
    sender: "Receipts <receipts@example.com>",
    subject: "Your receipt",
    received_at: "2026-09-01T09:30:00Z",
    template_id: null,
    representation: null,
};
const emailPage = (page = 1, items = [message], total = 51) => ({
    items,
    total,
    page,
    page_size: 50,
    total_pages: Math.ceil(total / 50),
});

async function fillSync(page: Page) {
    await page.getByLabel("Gmail label").fill("Receipts");
    await page.getByLabel("Start date").fill("2026-09-01");
}

test("sync blocks duplicates, shows exact counts and refreshes page one", async ({ page }) => {
    let synced = false;
    let calls = 0;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
        release = resolve;
    });
    await page.route("**/api/emails?*", async (route) => {
        const number = Number(new URL(route.request().url()).searchParams.get("page"));
        await route.fulfill({
            json: emailPage(number, [
                {
                    ...message,
                    subject: synced ? "Newly stored receipt" : "Previously stored receipt",
                },
            ]),
        });
    });
    await page.route("**/api/email-sync", async (route) => {
        calls++;
        expect(route.request().postDataJSON()).toEqual({
            label: "Receipts",
            from_date: "2026-09-01",
        });
        await gate;
        synced = true;
        await route.fulfill({ json: { pulled: 7, inserted: 3, already_stored: 4 } });
    });
    await page.goto("/emails?page=1");
    await expect(page.getByText("Previously stored receipt")).toBeVisible();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page).toHaveURL(/page=2/);
    await fillSync(page);
    await page.getByRole("button", { name: "Sync emails", exact: true }).click();
    await expect(page.getByRole("button", { name: "Syncing…" })).toBeDisabled();
    await expect(page.getByLabel("Gmail label")).toBeDisabled();
    release();
    await expect(page.getByRole("status")).toContainText(
        "7 pulled · 3 inserted · 4 already stored",
    );
    await expect(page).toHaveURL(/page=1/);
    await expect(page.getByText("Newly stored receipt")).toBeVisible();
    await expect(page.getByRole("heading", { name: "All stored emails" })).toBeVisible();
    expect(calls).toBe(1);
});

test("sync failure preserves inputs and permits a successful retry", async ({ page }) => {
    await page.route("**/api/emails?*", (route) => route.fulfill({ json: emailPage(1, [], 0) }));
    let attempts = 0;
    await page.route("**/api/email-sync", (route) => {
        attempts++;
        return route.fulfill(
            attempts === 1
                ? { status: 503, json: { detail: "Gmail credentials are unavailable" } }
                : { json: { pulled: 0, inserted: 0, already_stored: 0 } },
        );
    });
    await page.goto("/emails");
    await fillSync(page);
    await page.getByRole("button", { name: "Sync emails", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText("Gmail credentials are unavailable");
    await expect(page.getByLabel("Gmail label")).toHaveValue("Receipts");
    await expect(page.getByLabel("Start date")).toHaveValue("2026-09-01");
    await page.getByRole("button", { name: "Sync emails", exact: true }).click();
    await expect(page.getByRole("status")).toContainText(
        "0 pulled · 0 inserted · 0 already stored",
    );
    expect(attempts).toBe(2);
});

test("pagination and detail preserve the page, body is inert text", async ({ page }) => {
    await page.route("**/api/emails?*", (route) => {
        const number = Number(new URL(route.request().url()).searchParams.get("page"));
        return route.fulfill({ json: emailPage(number) });
    });
    const body = '<img src=x onerror="alert(1)">\nReceipt total: 42.00';
    await page.route("**/api/emails/1", (route) => route.fulfill({ json: { ...message, body } }));
    await page.goto("/emails?page=1");
    await expect(page.getByRole("button", { name: "Previous" })).toBeDisabled();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.getByText("Page 2 of 2")).toBeVisible();
    await expect(page.getByRole("button", { name: "Next", exact: true })).toBeDisabled();
    await page.getByRole("link", { name: /Your receipt/ }).click();
    await expect(page).toHaveURL("/emails/1?page=2");
    await expect(page.getByRole("heading", { name: "Your receipt" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Email body" })).toHaveText(body);
    await expect(page.locator(".email-body img")).toHaveCount(0);
    await expect(page.getByText(message.sender)).toBeVisible();
    await expect(page.locator("time")).toHaveAttribute("datetime", message.received_at);
    await page.getByRole("link", { name: "Back to emails" }).click();
    await expect(page).toHaveURL("/emails?page=2");
    await page.reload();
    await expect(page.getByText("Page 2 of 2")).toBeVisible();
});

test("list loading, connection error, retry and empty states", async ({ page }) => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
        release = resolve;
    });
    await page.route("**/api/emails?*", async (route) => {
        await gate;
        await route.abort();
    });
    await page.goto("/emails");
    await expect(page.getByRole("status")).toHaveText("Loading emails…");
    release();
    await expect(page.getByRole("alert")).toContainText("Could not reach the Aggregator API");
    await page.route("**/api/emails?*", (route) => route.fulfill({ json: emailPage(1, [], 0) }));
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByRole("heading", { name: "No emails stored yet" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Next", exact: true })).toBeDisabled();
});

test("detail loading, server error, retry and missing email", async ({ page }) => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
        release = resolve;
    });
    await page.route("**/api/emails/1", async (route) => {
        await gate;
        await route.fulfill({ status: 500, body: "Internal Server Error" });
    });
    await page.goto("/emails/1");
    await expect(page.getByRole("status")).toHaveText("Loading email…");
    release();
    await expect(page.getByRole("alert")).toBeVisible();
    await page.route("**/api/emails/1", (route) =>
        route.fulfill({ status: 404, json: { detail: "Email not found" } }),
    );
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByRole("heading", { name: "Email not found" })).toBeVisible();
});

test("invalid and out-of-range pages recover; long content fits the viewport", async ({ page }) => {
    const requests: number[] = [];
    await page.route("**/api/emails?*", (route) => {
        const number = Number(new URL(route.request().url()).searchParams.get("page"));
        requests.push(number);
        return route.fulfill({
            json: emailPage(
                number,
                number > 2
                    ? []
                    : [
                          {
                              ...message,
                              subject: "Long subject ".repeat(50),
                              sender: "sender".repeat(50) + "@example.com",
                          },
                      ],
            ),
        });
    });
    await page.goto("/emails?page=invalid");
    await expect(page.getByText("Page 1 of 2")).toBeVisible();
    expect(requests[0]).toBe(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
    );
    await page.goto("/emails?page=9");
    await expect(page.getByRole("heading", { name: "No emails on this page" })).toBeVisible();
    await page.getByRole("link", { name: "Go to first page" }).click();
    await expect(page).toHaveURL("/emails?page=1");
});
