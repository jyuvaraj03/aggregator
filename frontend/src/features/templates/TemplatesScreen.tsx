import { useEffect, useRef } from "react";
import { useIsMutating, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorState, Pagination, readPage } from "../../components/shared";
import { errorMessage } from "../../lib/api/client";
import { emailKeys } from "../emails/queries";
import { extractionKey, extractTemplates, templateKeys, templatePageOptions } from "./queries";
import { templateHref } from "./navigation";

export function TemplatesScreen() {
    const [search, setSearch] = useSearchParams();
    const page = readPage(search.get("page"));
    const templates = useQuery(templatePageOptions(page));
    const client = useQueryClient();
    const submitting = useRef(false);
    const mounted = useRef(true);
    useEffect(() => {
        mounted.current = true;
        return () => {
            mounted.current = false;
        };
    }, []);
    const extracting = useIsMutating({ mutationKey: extractionKey }) > 0;
    const extraction = useMutation({
        mutationKey: extractionKey,
        mutationFn: extractTemplates,
        retry: false,
        onSuccess: async () => {
            // Discard pre-extraction reads before refreshing assignments and counts.
            await Promise.all(
                [emailKeys.all, templateKeys.all].map(async (queryKey) => {
                    await client.cancelQueries({ queryKey });
                    await client.invalidateQueries({ queryKey, refetchType: "none" });
                }),
            );
            if (mounted.current) setSearch({ page: "1" });
            // Read errors belong to the list; a successful extraction stays successful.
            await Promise.all([
                client.refetchQueries({ queryKey: emailKeys.all, type: "active" }),
                client.refetchQueries({ queryKey: templateKeys.all, type: "active" }),
            ]);
        },
    });

    return (
        <>
            <header className="page-heading">
                <h1>Templates</h1>
                <p>Find reusable patterns in your emails. Inspect the messages they match.</p>
            </header>
            <section className="sync-panel" aria-labelledby="extract-heading">
                <div className="extraction-controls">
                    <div>
                        <h2 id="extract-heading">Extract templates</h2>
                        <p>
                            Process all stored emails without a template. Emails already assigned
                            keep their template.
                        </p>
                    </div>
                    <button
                        disabled={extracting}
                        onClick={async () => {
                            if (submitting.current || extracting) return;
                            submitting.current = true;
                            try {
                                await extraction.mutateAsync();
                            } catch {
                                /* Display the mutation error below. */
                            } finally {
                                submitting.current = false;
                            }
                        }}
                    >
                        {extracting ? "Extracting…" : "Extract templates"}
                    </button>
                </div>
                {extracting && (
                    <p role="status">
                        Finding patterns and assigning templates. This may take a moment.
                    </p>
                )}
                {extraction.isError && (
                    <p className="error sync-message" role="alert">
                        {errorMessage(extraction.error)}
                    </p>
                )}
                {extraction.isSuccess && (
                    <p className="success sync-message" role="status">
                        <strong>Extraction complete.</strong> {extraction.data.processed} processed
                        · {extraction.data.skipped} skipped · {extraction.data.templates_created}{" "}
                        templates created
                        {extraction.data.skipped > 0 && (
                            <span className="result-note">
                                Emails with empty or whitespace-only bodies were skipped.
                            </span>
                        )}
                    </p>
                )}
            </section>
            <section
                className="email-list"
                aria-labelledby="templates-heading"
                aria-busy={templates.isFetching}
            >
                <div className="section-heading">
                    <div>
                        <h2 id="templates-heading">All templates</h2>
                        <p>Open a template to inspect its pattern and matching emails.</p>
                    </div>
                    {templates.data && (
                        <span className="total">{templates.data.total.toLocaleString()} total</span>
                    )}
                </div>
                {templates.isPending && (
                    <div className="state" role="status">
                        Loading templates…
                    </div>
                )}
                {templates.isError && (
                    <ErrorState
                        error={templates.error}
                        retry={() => {
                            void templates.refetch();
                        }}
                    />
                )}
                {templates.data && (
                    <>
                        {templates.data.items.length ? (
                            <ul className="messages">
                                {templates.data.items.map((template) => (
                                    <li key={template.id}>
                                        <Link
                                            className="email-row template-row"
                                            to={templateHref(template.id, page)}
                                        >
                                            <span className="email-copy">
                                                <span className="template-name">
                                                    Template {template.id}
                                                </span>
                                                <span className="template-preview">
                                                    {template.text}
                                                </span>
                                            </span>
                                            <span className="total">
                                                {template.email_count.toLocaleString()}{" "}
                                                {template.email_count === 1 ? "email" : "emails"}
                                            </span>
                                            <svg
                                                className="chevron"
                                                viewBox="0 0 24 24"
                                                aria-hidden="true"
                                            >
                                                <path d="m9 5 7 7-7 7" />
                                            </svg>
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <div className="state">
                                <h3>
                                    {templates.data.total === 0
                                        ? "No templates yet"
                                        : "No templates on this page"}
                                </h3>
                                <p>
                                    {templates.data.total === 0
                                        ? "Sync your emails, then extract templates using the button above."
                                        : "Return to the first page to browse templates."}
                                </p>
                                {templates.data.total === 0 && (
                                    <Link to="/emails">Go to emails</Link>
                                )}
                                {page > 1 && <Link to="/templates?page=1">Go to first page</Link>}
                            </div>
                        )}
                        <Pagination
                            page={page}
                            totalPages={templates.data.total_pages}
                            label="Template pages"
                            onPage={(next) => setSearch({ page: String(next) })}
                        />
                    </>
                )}
            </section>
        </>
    );
}
