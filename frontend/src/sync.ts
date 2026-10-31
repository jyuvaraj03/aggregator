import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  readStorage,
  request,
  writeStorage,
  type Job,
  type SyncSession,
} from "./api";

const STORAGE_KEY = "aggregator-sync-session";
let submission: Promise<SyncSession> | undefined;
const completedJobs = new Map<string, Job>();

export function fromDate(
  now = new Date(),
  days = Number(import.meta.env.VITE_SYNC_LOOKBACK_DAYS ?? 30),
) {
  if (!Number.isInteger(days) || days < 1)
    throw new Error("VITE_SYNC_LOOKBACK_DAYS must be a positive whole number.");
  const date = new Date(now);
  date.setDate(date.getDate() - days);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function storedSession(): SyncSession | undefined {
  try {
    const value = JSON.parse(
      readStorage(sessionStorage, STORAGE_KEY) ?? "null",
    );
    if (
      typeof value?.jobId === "string" &&
      value.jobId &&
      /^\d{4}-\d{2}-\d{2}$/.test(value.fromDate)
    )
      return value;
  } catch {
    /* Ignore malformed session data. */
  }
}
function submit(date: string): Promise<SyncSession> {
  return request<{ job_id: string }>("/email-sync", {
    method: "POST",
    body: JSON.stringify({ from_date: date }),
  })
    .then((job) => {
      const session = { jobId: job.job_id, fromDate: date };
      writeStorage(sessionStorage, STORAGE_KEY, JSON.stringify(session));
      return session;
    })
    .catch((error) => {
      submission = undefined;
      throw error;
    });
}
export function getOrStartSession(): Promise<SyncSession> {
  const saved = storedSession();
  if (saved) return Promise.resolve(saved);
  return (submission ??= submit(fromDate()));
}

export interface Pipeline {
  state: "working" | "ready" | "failed";
  label: string;
  templateCount: number;
}
async function job(id: string, signal?: AbortSignal) {
  const cached = completedJobs.get(id);
  if (cached) return cached;
  const result = await request<Job>(`/jobs/${encodeURIComponent(id)}`, {
    signal,
  });
  if (result.status === "succeeded") completedJobs.set(id, result);
  return result;
}
function stage(jobs: Job[], label: string): Pipeline | undefined {
  const failed = jobs.find(
    (item) => item.status === "failed" || item.status === "superseded",
  );
  if (failed)
    return {
      state: "failed",
      label:
        failed.status === "superseded"
          ? "This sync was replaced by another run. Restart sync to continue."
          : `${label.replace(/…$/, "")} failed. Restart sync to try again.`,
      templateCount: 0,
    };
  if (jobs.some((item) => item.status !== "succeeded"))
    return { state: "working", label, templateCount: 0 };
}
function childId(value: unknown): string {
  if (typeof value !== "string" || !value)
    throw new Error(
      "The processing job returned an incomplete result. Retry checking.",
    );
  return value;
}
export async function checkPipeline(
  session: SyncSession,
  signal?: AbortSignal,
): Promise<Pipeline> {
  const sync = await job(session.jobId, signal);
  const syncStage = stage([sync], "Syncing emails…");
  if (syncStage) return syncStage;
  const assignment = await job(
    childId(sync.result?.template_assignment_job_id),
    signal,
  );
  const assignmentStage = stage([assignment], "Finding email templates…");
  if (assignmentStage) return assignmentStage;
  const children = assignment.result?.template_classification_jobs;
  const templateCount = assignment.result?.templates_created;
  if (!Array.isArray(children) || typeof templateCount !== "number")
    throw new Error(
      "The template job returned an incomplete result. Retry checking.",
    );
  const classifications = await Promise.all(
    children.map((child) => job(childId(child.job_id), signal)),
  );
  const classificationStage = stage(
    classifications,
    "Identifying transaction emails…",
  );
  if (classificationStage) return classificationStage;
  const parsers = await Promise.all(
    classifications.flatMap((classification) => {
      const id = classification.result?.parser_generation_job_id;
      if (id === null) return [];
      return [job(childId(id), signal)];
    }),
  );
  return (
    stage(parsers, "Preparing transaction tags…") ?? {
      state: "ready",
      label: "Templates are ready",
      templateCount,
    }
  );
}
export function useSync() {
  const client = useQueryClient();
  const session = useQuery({
    queryKey: ["sync-session"],
    queryFn: getOrStartSession,
    staleTime: Infinity,
    gcTime: Infinity,
    retry: false,
  });
  const pipeline = useQuery({
    queryKey: ["sync-pipeline", session.data?.jobId],
    queryFn: ({ signal }) => checkPipeline(session.data!, signal),
    enabled: !!session.data,
    retry: false,
    refetchInterval: (query) =>
      query.state.error ||
      (query.state.data?.state !== "working" && query.state.data)
        ? false
        : 2000,
    refetchOnWindowFocus: false,
  });
  return {
    session,
    pipeline,
    retry: () => (session.isError ? session.refetch() : pipeline.refetch()),
    restart: async () => {
      if (!session.data) return;
      submission = submit(session.data.fromDate);
      const next = await submission;
      client.setQueryData(["sync-session"], next);
    },
  };
}
