import { expect, it, vi } from "vitest";
import { listAccounts, saveAccount, deleteAccount } from "./api";
it("loads every account page in creation order", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string) =>
      Response.json({
        items: path.endsWith("page=1") ? [{ id: 3 }, { id: 2 }] : [{ id: 1 }],
        total_pages: 2,
      }),
    ),
  );
  expect((await listAccounts()).map((account) => account.id)).toEqual([
    1, 2, 3,
  ]);
  expect(fetch).toHaveBeenCalledTimes(2);
});
it("sends themes when creating and updating accounts", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ id: 1, name: "Travel", color: 4 })),
  );
  await saveAccount(null, "Travel", 4);
  expect(fetch).toHaveBeenLastCalledWith(
    "/api/accounts",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ name: "Travel", color: 4 }),
    }),
  );
  await saveAccount(1, "Trips", 5);
  expect(fetch).toHaveBeenLastCalledWith(
    "/api/accounts/1",
    expect.objectContaining({ method: "PATCH" }),
  );
});
it("surfaces removal conflicts and handles empty deletes", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      Response.json(
        { detail: "This account has saved transactions." },
        { status: 409 },
      ),
    ),
  );
  await expect(deleteAccount(1)).rejects.toThrow("saved transactions");
  vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));
  await expect(deleteAccount(1)).resolves.toBeUndefined();
});
