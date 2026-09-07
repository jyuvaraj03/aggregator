import { queryOptions } from "@tanstack/react-query";
import { api, apiError } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

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

export async function syncEmails(body: components["schemas"]["EmailSyncRequest"]) {
    const { data, error, response } = await api.POST("/email-sync", { body });
    if (!data) throw apiError(response.status, error);
    return data;
}
