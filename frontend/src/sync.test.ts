import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Job } from "./api";
const success = (job_id: string, result: Record<string, unknown>): Job => ({
  job_id,
  status: "succeeded",
  result,
  error: null,
});
let jobs: Record<string, Job>;
let sync: typeof import("./sync");
const session = { jobId: "sync", fromDate: "2026-10-01" };
beforeEach(async () => {
  vi.resetModules();
  sync = await import("./sync");
  jobs = {
    sync: success("sync", { template_assignment_job_id: "assign" }),
    assign: success("assign", {
      templates_created: 1,
      template_classification_jobs: [{ template_id: 1, job_id: "classify" }],
    }),
    classify: success("classify", { parser_generation_job_id: "parser" }),
    parser: success("parser", {}),
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, init?: RequestInit) => {
      if (init?.method === "POST") return Response.json({ job_id: "sync" });
      const id = path.split("/").pop()!;
      if (!jobs[id]) throw new Error(`Unexpected job ${id}`);
      return Response.json(jobs[id]);
    }),
  );
});
describe("sync pipeline", () => {
  it("computes calendar dates across year boundaries", () => {
    expect(sync.fromDate(new Date(2026, 0, 15), 30)).toBe("2025-12-16");
    expect(() => sync.fromDate(new Date(), 0)).toThrow("positive whole number");
  });
  it("submits once for concurrent mounts and resumes after refresh", async () => {
    const [a, b] = await Promise.all([
      sync.getOrStartSession(),
      sync.getOrStartSession(),
    ]);
    expect(a).toEqual(b);
    expect(fetch).toHaveBeenCalledTimes(1);
    vi.resetModules();
    const reloaded = await import("./sync");
    expect(await reloaded.getOrStartSession()).toEqual(a);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("waits for the complete chain", async () => {
    expect(await sync.checkPipeline(session)).toEqual({
      state: "ready",
      label: "Templates are ready",
      templateCount: 1,
    });
    expect(fetch).toHaveBeenCalledTimes(4);
  });
  it.each([
    ["sync", "Syncing emails…"],
    ["assign", "Finding email templates…"],
    ["classify", "Identifying transaction emails…"],
    ["parser", "Preparing transaction tags…"],
  ])("waits for %s", async (id, label) => {
    jobs[id] = { job_id: id, status: "retrying", result: null, error: null };
    expect(await sync.checkPipeline(session)).toMatchObject({
      state: "working",
      label,
    });
  });
  it.each(["sync", "assign", "classify", "parser"])(
    "reports failure at %s",
    async (id) => {
      jobs[id] = {
        job_id: id,
        status: "failed",
        result: null,
        error: "Job failed",
      };
      expect(await sync.checkPipeline(session)).toMatchObject({
        state: "failed",
      });
    },
  );
  it("reports superseded runs", async () => {
    jobs.assign.status = "superseded";
    expect(await sync.checkPipeline(session)).toMatchObject({
      state: "failed",
      label: expect.stringContaining("replaced"),
    });
  });
  it("accepts no new templates", async () => {
    jobs.assign = success("assign", {
      templates_created: 0,
      template_classification_jobs: [],
    });
    expect(await sync.checkPipeline(session)).toMatchObject({
      state: "ready",
      templateCount: 0,
    });
  });
  it("accepts classification without a parser job", async () => {
    jobs.classify = success("classify", { parser_generation_job_id: null });
    expect(await sync.checkPipeline(session)).toMatchObject({ state: "ready" });
    expect(fetch).toHaveBeenCalledTimes(3);
  });
  it("recovers polling errors without re-fetching completed parents", async () => {
    jobs.parser.status = "running";
    await sync.checkPipeline(session);
    vi.mocked(fetch).mockRejectedValueOnce(new Error("Network unavailable"));
    await expect(sync.checkPipeline(session)).rejects.toThrow(
      "Network unavailable",
    );
    jobs.parser.status = "succeeded";
    expect(await sync.checkPipeline(session)).toMatchObject({ state: "ready" });
    expect(fetch).toHaveBeenCalledTimes(6);
  });
  it("rejects incomplete successful results", async () => {
    jobs.assign.result = {};
    await expect(sync.checkPipeline(session)).rejects.toThrow(
      "incomplete result",
    );
  });
});
