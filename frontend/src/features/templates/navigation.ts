import { readPage } from "../../components/shared";

export const DEFAULT_TEMPLATE_VIEW = "alerts_and_needs_review";

export type TemplateView =
    | typeof DEFAULT_TEMPLATE_VIEW
    | "transaction_alert"
    | "unclassified"
    | "not_transaction_alert"
    | "all";

const templateViews = new Set<TemplateView>([
    DEFAULT_TEMPLATE_VIEW,
    "transaction_alert",
    "unclassified",
    "not_transaction_alert",
    "all",
]);

export function readTemplateView(value: string | null): TemplateView {
    return value && templateViews.has(value as TemplateView)
        ? (value as TemplateView)
        : DEFAULT_TEMPLATE_VIEW;
}

function addTemplateView(search: URLSearchParams, view: TemplateView) {
    if (view !== DEFAULT_TEMPLATE_VIEW) search.set("classification", view);
    return search;
}

export function templateListSearch(view: TemplateView, page: number) {
    return addTemplateView(new URLSearchParams({ page: String(page) }), view);
}

export function templateListHref(page: number, view: TemplateView) {
    return `/templates?${templateListSearch(view, page)}`;
}

export function templateDetailSearch(view: TemplateView, page: number, emailsPage: number) {
    return addTemplateView(
        new URLSearchParams({ page: String(page), emailsPage: String(emailsPage) }),
        view,
    );
}

export function templateHref(
    id: number,
    page: number,
    emailsPage = 1,
    view: TemplateView = DEFAULT_TEMPLATE_VIEW,
) {
    return `/templates/${id}?${templateDetailSearch(view, page, emailsPage)}`;
}

export function templateEmailHref(
    emailId: number,
    templateId: number,
    templatePage: number,
    emailsPage: number,
    view: TemplateView,
) {
    const search = addTemplateView(
        new URLSearchParams({
            fromTemplate: String(templateId),
            templatePage: String(templatePage),
            emailsPage: String(emailsPage),
        }),
        view,
    );
    return `/emails/${emailId}?${search}`;
}

export function templateOrigin(search: URLSearchParams) {
    const rawId = search.get("fromTemplate");
    const id = Number(rawId);
    if (!rawId || !/^\d+$/.test(rawId) || !Number.isSafeInteger(id) || id <= 0) return null;
    const view = readTemplateView(search.get("classification"));
    return {
        id,
        view,
        href: templateHref(
            id,
            readPage(search.get("templatePage")),
            readPage(search.get("emailsPage")),
            view,
        ),
    };
}
