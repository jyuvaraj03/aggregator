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
        : "Could not reach the email API. Check that the backend is running, then try again.";
}
