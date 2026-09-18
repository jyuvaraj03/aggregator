import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorState, Pagination, readPage } from "../../components/shared";
import { templatePageOptions } from "./queries";
import { templateHref } from "./navigation";

export function TemplatesScreen() {
    const [search, setSearch] = useSearchParams();
    const page = readPage(search.get("page"));
    const templates = useQuery(templatePageOptions(page));

    return (
        <>
            <header className="page-heading">
                <h1>Templates</h1>
                <p>Find reusable patterns in your emails. Inspect the messages they match.</p>
            </header>
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
                                        ? "Sync your emails to create templates automatically."
                                        : "Return to the first page to browse templates."}
                                </p>
                                {templates.data.total === 0 && (
                                    <Link to="/emails">Sync emails</Link>
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
