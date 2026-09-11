import { queryOptions } from "@tanstack/react-query";
import { api, apiError, waitForJob } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

export type SyncResult = {
    pulled: number;
    inserted: number;
    already_stored: number;
};

export const emailKeys = { all: ["emails"] as const };

export function emailPageOptions(page: number, templateId?: number) {
    return queryOptions({
        queryKey: [...emailKeys.all, "list", page, templateId ?? "all"],
        queryFn: async ({ signal }) => {
            const { data, error, response } = await api.GET("/emails", {
                params: { query: { page, template_id: templateId } },
                signal,
            });
            if (!data) throw apiError(response.status, error);
            return data;
        },
    });
}

export function emailDetailOptions(id: number) {
    return queryOptions({
        queryKey: [...emailKeys.all, "detail", id],
        queryFn: async ({ signal }) => {
            const { data, error, response } = await api.GET("/emails/{email_id}", {
                params: { path: { email_id: id } },
                signal,
            });
            if (!data) throw apiError(response.status, error);
            return data;
        },
    });
}

export async function syncEmails(
    body: components["schemas"]["EmailSyncRequest"],
): Promise<SyncResult> {
    const {
        data: submitted,
        error: submitError,
        response: submitResponse,
    } = await api.POST("/email-sync", { body });
    if (!submitted) throw apiError(submitResponse.status, submitError);

    return waitForJob(submitted.job_id, isSyncResult);
}

function isSyncResult(value: object | null | undefined): value is SyncResult {
    const result = value as Record<string, unknown> | null;
    return (
        result !== null &&
        typeof result.pulled === "number" &&
        typeof result.inserted === "number" &&
        typeof result.already_stored === "number"
    );
}
