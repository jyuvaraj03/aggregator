import { queryOptions } from "@tanstack/react-query";
import { api, apiError, waitForJob } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";

export type TemplateClassification = components["schemas"]["TemplateClassification"];
export type FieldParserSet = components["schemas"]["FieldParserSet"];
export type FieldParserSnapshot = components["schemas"]["TemplateFieldParsersResponse"];

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

export function fieldParserOptions(id: number) {
    return queryOptions({
        queryKey: [...templateKeys.all, "detail", id, "field-parsers"],
        queryFn: async ({ signal }) => {
            const { data, error, response } = await api.GET(
                "/templates/{template_id}/field-parsers",
                {
                    params: { path: { template_id: id } },
                    signal,
                },
            );
            if (!data) throw apiError(response.status, error);
            return data;
        },
    });
}

export async function saveFieldParsers(input: { id: number; parsers: FieldParserSet }) {
    const { data, error, response } = await api.PUT("/templates/{template_id}/field-parsers", {
        params: { path: { template_id: input.id } },
        body: input.parsers,
    });
    if (!data) throw apiError(response.status, error);
    return data;
}

export async function approveFieldParsers(id: number) {
    const { data, error, response } = await api.POST(
        "/templates/{template_id}/field-parsers/approve",
        { params: { path: { template_id: id } } },
    );
    if (!data) throw apiError(response.status, error);
    return data;
}

export async function generateFieldParsers(id: number): Promise<FieldParserSnapshot> {
    const {
        data: submitted,
        error: submitError,
        response: submitResponse,
    } = await api.POST("/templates/{template_id}/field-parsers/generate", {
        params: { path: { template_id: id } },
    });
    if (!submitted) throw apiError(submitResponse.status, submitError);
    return waitForJob(submitted.job_id, isFieldParserSnapshot);
}

function isFieldParserSnapshot(value: object | null | undefined): value is FieldParserSnapshot {
    const result = value as Record<string, unknown> | null;
    return (
        result !== null &&
        typeof result.template_id === "number" &&
        typeof result.text === "string" &&
        Array.isArray(result.parameters) &&
        typeof result.parsers === "object" &&
        result.parsers !== null &&
        (result.field_parser_status === "needs_generation" ||
            result.field_parser_status === "needs_review" ||
            result.field_parser_status === "approved")
    );
}
