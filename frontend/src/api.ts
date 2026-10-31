export interface Account {
  id: number;
  name: string;
  color: number;
}
interface Page<T> {
  items: T[];
  total_pages: number;
}
export interface Job {
  job_id: string;
  status:
    "queued" | "running" | "retrying" | "succeeded" | "failed" | "superseded";
  result: Record<string, unknown> | null;
  error: string | null;
}
export interface SyncSession {
  jobId: string;
  fromDate: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message =
      typeof body?.detail === "string"
        ? body.detail
        : `Request failed (${response.status}). Please try again.`;
    throw new ApiError(message, response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export async function listAccounts(signal?: AbortSignal): Promise<Account[]> {
  const accounts: Account[] = [];
  let page = 1;
  let totalPages: number;
  do {
    const result = await request<Page<Account>>(`/accounts?page=${page}`, {
      signal,
    });
    accounts.push(...result.items);
    totalPages = result.total_pages;
    page += 1;
  } while (page <= totalPages);
  return accounts.sort((a, b) => a.id - b.id);
}
export const saveAccount = (id: number | null, name: string, color: number) =>
  request<Account>(id === null ? "/accounts" : `/accounts/${id}`, {
    method: id === null ? "POST" : "PATCH",
    body: JSON.stringify({ name, color }),
  });
export const deleteAccount = (id: number) =>
  request<void>(`/accounts/${id}`, { method: "DELETE" });

export function readStorage(storage: Storage, key: string): string | null {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}
export function writeStorage(storage: Storage, key: string, value: string) {
  try {
    storage.setItem(key, value);
  } catch {
    /* Continue without persistence when storage is unavailable. */
  }
}
