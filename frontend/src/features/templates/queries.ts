import { queryOptions } from "@tanstack/react-query";
import { api, apiError } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

export type TemplateClassification = components["schemas"]["TemplateClassification"];

export const templateKeys = { all: ["templates"] as const };

export function templatePageOptions(
    page: number,
    classifications: readonly TemplateClassification[] | undefined,
) {
    return queryOptions({
        queryKey: [...templateKeys.all, "list", page, ...(classifications ?? ["all"])],
        queryFn: async ({ signal }) => {
            const { data, error, response } = await api.GET("/templates", {
                params: {
                    query: {
                        page,
                        classification: classifications ? [...classifications] : undefined,
                    },
                },
                signal,
            });
            if (!data) throw apiError(response.status, error);
            return data;
        },
    });
}

export function templateDetailOptions(id: number) {
    return queryOptions({
        queryKey: [...templateKeys.all, "detail", id],
        queryFn: async ({ signal }) => {
            const { data, error, response } = await api.GET("/templates/{template_id}", {
                params: { path: { template_id: id } },
                signal,
            });
            if (!data) throw apiError(response.status, error);
            return data;
        },
    });
}
