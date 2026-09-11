import { queryOptions } from "@tanstack/react-query";
import { api, apiError, waitForJob } from "../../lib/api/client";

export const templateKeys = { all: ["templates"] as const };
export const extractionKey = ["extract-templates"] as const;

export type TemplateExtractionResult = {
    processed: number;
    skipped: number;
    templates_created: number;
};

export function templatePageOptions(page: number) {
    return queryOptions({
        queryKey: [...templateKeys.all, "list", page],
        queryFn: async ({ signal }) => {
            const { data, error, response } = await api.GET("/templates", {
                params: { query: { page } },
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

export async function extractTemplates(): Promise<TemplateExtractionResult> {
    const { data: submitted, error, response } = await api.POST("/email-template-assignment");
    if (!submitted) throw apiError(response.status, error);
    return waitForJob(submitted.job_id, isTemplateExtractionResult);
}

function isTemplateExtractionResult(
    value: object | null | undefined,
): value is TemplateExtractionResult {
    const result = value as Record<string, unknown> | null;
    return (
        result !== null &&
        typeof result.processed === "number" &&
        typeof result.skipped === "number" &&
        typeof result.templates_created === "number"
    );
}
