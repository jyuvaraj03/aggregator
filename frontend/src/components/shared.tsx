import { errorMessage } from "../lib/api/client";

export function Pagination({
    page,
    totalPages,
    label,
    onPage,
}: {
    page: number;
    totalPages: number;
    label: string;
    onPage: (page: number) => void;
}) {
    return (
        <nav className="pagination" aria-label={label}>
            <button className="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>
                Previous
            </button>
            <span>{totalPages > 0 ? `Page ${page} of ${totalPages}` : "Page 1"}</span>
            <button
                className="secondary"
                disabled={page >= totalPages}
                onClick={() => onPage(page + 1)}
            >
                Next
            </button>
        </nav>
    );
}

export function readPage(value: string | null): number {
    const page = Number(value);
    return Number.isSafeInteger(page) && page > 0 ? page : 1;
}

export function ReceivedTime({ value }: { value: string }) {
    const date = new Date(value);
    return (
        <time dateTime={value} title={value}>
            {Number.isNaN(date.getTime())
                ? value
                : new Intl.DateTimeFormat(undefined, {
                      dateStyle: "medium",
                      timeStyle: "short",
                  }).format(date)}
        </time>
    );
}

export function ErrorState({ error, retry }: { error: Error; retry: () => void }) {
    return (
        <div className="state error" role="alert">
            <p>{errorMessage(error)}</p>
            <button type="button" className="secondary" onClick={retry}>
                Try again
            </button>
        </div>
    );
}
