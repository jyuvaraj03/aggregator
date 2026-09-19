import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { EmailRows } from "../../components/EmailRows";
import { ErrorState, Pagination, readPage, ReceivedTime } from "../../components/shared";
import { ApiError } from "../../lib/api/client";
import { emailPageOptions } from "../emails/queries";
import { templateDetailOptions } from "./queries";
import {
    readTemplateView,
    templateDetailSearch,
    templateEmailHref,
    templateHref,
    templateListHref,
} from "./navigation";

export function TemplateDetailScreen() {
    const { templateId } = useParams();
    const [search, setSearch] = useSearchParams();
    const page = readPage(search.get("page"));
    const emailsPage = readPage(search.get("emailsPage"));
    const view = readTemplateView(search.get("classification"));
    const id = Number(templateId);
    const validId = Number.isSafeInteger(id) && id > 0;
    const template = useQuery({ ...templateDetailOptions(id), enabled: validId });
    const missing =
        !validId || (template.error instanceof ApiError && template.error.status === 404);
    const emails = useQuery({
        ...emailPageOptions(emailsPage, id),
        enabled: validId && template.isSuccess,
    });
    const emailHref = (emailId: number) => templateEmailHref(emailId, id, page, emailsPage, view);

    return (
        <>
            <Link className="back-link" to={templateListHref(page, view)}>
                Back to templates
            </Link>
            {missing ? (
                <div className="state">
                    <h1>Template not found</h1>
                    <p>
                        This template is unavailable. Return to the list to choose another template.
                    </p>
                </div>
            ) : template.isPending ? (
                <div className="state" role="status">
                    Loading template…
                </div>
            ) : template.isError ? (
                <ErrorState
                    error={template.error}
                    retry={() => {
                        void template.refetch();
                    }}
                />
            ) : (
                <>
                    <header className="page-heading">
                        <h1>Template {template.data.id}</h1>
                        <p>
                            {template.data.email_count.toLocaleString()} matching{" "}
                            {template.data.email_count === 1 ? "email" : "emails"}
                        </p>
                    </header>
                    <section className="template-section" aria-labelledby="pattern-heading">
                        <h2 id="pattern-heading">Template pattern</h2>
                        <pre className="template-pattern">{template.data.text}</pre>
                    </section>
                    <section className="template-section" aria-labelledby="example-heading">
                        <h2 id="example-heading">Example email</h2>
                        {template.data.example ? (
                            <article className="email-detail template-example">
                                <h3>
                                    <Link to={emailHref(template.data.example.id)}>
                                        {template.data.example.subject || "(No subject)"}
                                    </Link>
                                </h3>
                                <dl>
                                    <div>
                                        <dt>From</dt>
                                        <dd>{template.data.example.sender || "Unknown sender"}</dd>
                                    </div>
                                    <div>
                                        <dt>Received</dt>
                                        <dd>
                                            <ReceivedTime
                                                value={template.data.example.received_at}
                                            />
                                        </dd>
                                    </div>
                                </dl>
                                <div className="email-body">
                                    {template.data.example.body || "This email has no body."}
                                </div>
                            </article>
                        ) : (
                            <p className="example-empty">
                                No example email is available for this template.
                            </p>
                        )}
                    </section>
                    <section
                        className="email-list"
                        aria-labelledby="matching-heading"
                        aria-busy={emails.isFetching}
                    >
                        <div className="section-heading">
                            <h2 id="matching-heading">Matching emails</h2>
                            {emails.data && (
                                <span className="total">
                                    {emails.data.total.toLocaleString()} total
                                </span>
                            )}
                        </div>
                        {emails.isPending && (
                            <div className="state" role="status">
                                Loading matching emails…
                            </div>
                        )}
                        {emails.isError && (
                            <ErrorState
                                error={emails.error}
                                retry={() => {
                                    void emails.refetch();
                                }}
                            />
                        )}
                        {emails.data && (
                            <>
                                {emails.data.items.length ? (
                                    <EmailRows emails={emails.data.items} href={emailHref} />
                                ) : (
                                    <div className="state">
                                        <h3>
                                            {emails.data.total === 0
                                                ? "No matching emails"
                                                : "No emails on this page"}
                                        </h3>
                                        <p>
                                            {emails.data.total === 0
                                                ? "There are no stored emails assigned to this template."
                                                : "Return to the first page to browse matching emails."}
                                        </p>
                                        {emailsPage > 1 && (
                                            <Link to={templateHref(id, page, 1, view)}>
                                                Go to first page
                                            </Link>
                                        )}
                                    </div>
                                )}
                                <Pagination
                                    page={emailsPage}
                                    totalPages={emails.data.total_pages}
                                    label="Matching email pages"
                                    onPage={(next) =>
                                        setSearch(templateDetailSearch(view, page, next))
                                    }
                                />
                            </>
                        )}
                    </section>
                </>
            )}
        </>
    );
}
