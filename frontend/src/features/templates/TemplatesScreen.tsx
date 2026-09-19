import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorState, Pagination, readPage } from "../../components/shared";
import {
    DEFAULT_TEMPLATE_VIEW,
    readTemplateView,
    templateHref,
    templateListHref,
    templateListSearch,
    type TemplateView,
} from "./navigation";
import { templatePageOptions, type TemplateClassification } from "./queries";

type TemplateViewOption = {
    id: TemplateView;
    label: string;
    classifications: readonly TemplateClassification[] | undefined;
    emptyHeading: string;
    emptyDescription: string;
};

const templateViewOptions: readonly TemplateViewOption[] = [
    {
        id: DEFAULT_TEMPLATE_VIEW,
        label: "Alerts & needs review",
        classifications: ["transaction_alert", "unclassified"],
        emptyHeading: "No alerts or templates needing review",
        emptyDescription: "No templates match either classification in this view.",
    },
    {
        id: "transaction_alert",
        label: "Transaction alerts",
        classifications: ["transaction_alert"],
        emptyHeading: "No transaction alerts",
        emptyDescription: "No templates are classified as transaction alerts.",
    },
    {
        id: "unclassified",
        label: "Needs review",
        classifications: ["unclassified"],
        emptyHeading: "No templates need review",
        emptyDescription: "Every template has a classification.",
    },
    {
        id: "not_transaction_alert",
        label: "Not transaction alerts",
        classifications: ["not_transaction_alert"],
        emptyHeading: "No non-transaction alerts",
        emptyDescription: "No templates are classified as not transaction alerts.",
    },
    {
        id: "all",
        label: "All templates",
        classifications: undefined,
        emptyHeading: "No templates yet",
        emptyDescription: "Sync your emails to create templates automatically.",
    },
];

function classificationBadge(classification: boolean | null) {
    if (classification === true) {
        return <span className="classification-badge alert">Transaction alert</span>;
    }
    if (classification === false) {
        return <span className="classification-badge not-alert">Not transaction alert</span>;
    }
    return <span className="classification-badge review">Needs review</span>;
}

export function TemplatesScreen() {
    const [search, setSearch] = useSearchParams();
    const page = readPage(search.get("page"));
    const view = readTemplateView(search.get("classification"));
    const selectedView =
        templateViewOptions.find((option) => option.id === view) ?? templateViewOptions[0]!;
    const templates = useQuery(templatePageOptions(page, selectedView.classifications));

    return (
        <>
            <header className="page-heading">
                <h1>Templates</h1>
                <p>Find reusable patterns in your emails. Inspect the messages they match.</p>
            </header>
            <nav className="classification-tabs" aria-label="Template classification views">
                {templateViewOptions.map((option) => (
                    <Link
                        key={option.id}
                        to={templateListHref(1, option.id)}
                        aria-current={option.id === view ? "page" : undefined}
                    >
                        {option.label}
                    </Link>
                ))}
            </nav>
            <section
                className="email-list"
                aria-labelledby="templates-heading"
                aria-busy={templates.isFetching}
            >
                <div className="section-heading">
                    <div>
                        <h2 id="templates-heading">{selectedView.label}</h2>
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
                                            to={templateHref(template.id, page, 1, view)}
                                        >
                                            <span className="email-copy">
                                                <span className="template-row-heading">
                                                    <span className="template-name">
                                                        Template {template.id}
                                                    </span>
                                                    {classificationBadge(
                                                        template.is_transaction_alert,
                                                    )}
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
                                        ? selectedView.emptyHeading
                                        : "No templates on this page"}
                                </h3>
                                <p>
                                    {templates.data.total === 0
                                        ? selectedView.emptyDescription
                                        : "Return to the first page to browse templates."}
                                </p>
                                {templates.data.total === 0 && view === "all" && (
                                    <Link to="/emails">Sync emails</Link>
                                )}
                                {page > 1 && (
                                    <Link to={templateListHref(1, view)}>Go to first page</Link>
                                )}
                            </div>
                        )}
                        <Pagination
                            page={page}
                            totalPages={templates.data.total_pages}
                            label="Template pages"
                            onPage={(next) => setSearch(templateListSearch(view, next))}
                        />
                    </>
                )}
            </section>
        </>
    );
}
