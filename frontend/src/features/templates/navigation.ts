import { readPage } from "../../components/shared";

export function templateHref(id: number, page: number, emailsPage = 1) {
    return `/templates/${id}?page=${page}&emailsPage=${emailsPage}`;
}

export function templateOrigin(search: URLSearchParams) {
    const rawId = search.get("fromTemplate");
    const id = Number(rawId);
    if (!rawId || !/^\d+$/.test(rawId) || !Number.isSafeInteger(id) || id <= 0) return null;
    return {
        id,
        href: templateHref(
            id,
            readPage(search.get("templatePage")),
            readPage(search.get("emailsPage")),
        ),
    };
}
