import { queryOptions } from "@tanstack/react-query";
import { api, apiError } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

export const emailKeys = { all: ["emails"] as const };

export function emailPageOptions(page: number) {
    return queryOptions({
        queryKey: [...emailKeys.all, "list", page],
        queryFn: async ({ signal }) => {
            const { data, error, response } = await api.GET("/emails", {
                params: { query: { page } },
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
