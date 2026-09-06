import { errorMessage } from "../../lib/api/client";

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
