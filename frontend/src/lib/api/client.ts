import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: "/api" });

export class ApiError extends Error {
    constructor(
        public readonly status: number,
        message: string,
    ) {
        super(message);
        this.name = "ApiError";
    }
}

export function apiError(status: number, error: unknown): ApiError {
    let message = `Request failed (${status}). Please try again.`;
    if (error && typeof error === "object" && "detail" in error) {
        if (typeof error.detail === "string") message = error.detail;
        else if (Array.isArray(error.detail)) {
            const messages = error.detail.flatMap((item: unknown) =>
                item && typeof item === "object" && "msg" in item && typeof item.msg === "string"
                    ? [item.msg]
                    : [],
            );
            if (messages.length) message = messages.join(" ");
        }
    }
    return new ApiError(status, message);
}

export function errorMessage(error: Error): string {
    return error instanceof ApiError
        ? error.message
        : "Could not reach the Aggregator API. Check that the backend is running, then try again.";
}

export async function waitForJob<Result extends object>(
    jobId: string,
    isResult: (value: object | null | undefined) => value is Result,
): Promise<Result> {
    while (true) {
        await new Promise((resolve) => window.setTimeout(resolve, 500));
        const { data, error, response } = await api.GET("/jobs/{job_id}", {
            params: { path: { job_id: jobId } },
        });
        if (!data) throw apiError(response.status, error);
        if (data.status === "failed")
            throw new ApiError(500, data.error ?? "Background job failed.");
        if (data.status === "succeeded") {
            if (isResult(data.result)) return data.result;
            throw new ApiError(
                500,
                "Background job completed without a valid result. Please try again.",
            );
        }
    }
}
