import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ApiError } from "../../lib/api/client";
import { emailDetailOptions } from "./queries";
import { ErrorState, readPage, ReceivedTime } from "../../components/shared";
import { templateOrigin } from "../templates/navigation";

export function EmailDetailScreen() {
    const { emailId } = useParams();
    const [search] = useSearchParams();
    const origin = templateOrigin(search);
    const id = Number(emailId);
    const validId = Number.isSafeInteger(id) && id > 0;
    const email = useQuery({ ...emailDetailOptions(id), enabled: validId });
    const missing = !validId || (email.error instanceof ApiError && email.error.status === 404);

    return (
        <>
            <Link
                className="back-link"
                to={origin?.href ?? `/emails?page=${readPage(search.get("page"))}`}
            >
                {origin ? "Back to template" : "Back to emails"}
            </Link>
            {missing ? (
                <div className="state">
                    <h1>Email not found</h1>
                    <p>This email is unavailable. Return to the list to choose another email.</p>
                </div>
            ) : email.isPending ? (
                <div className="state" role="status">
                    Loading email…
                </div>
            ) : email.isError ? (
                <ErrorState
                    error={email.error}
                    retry={() => {
                        void email.refetch();
                    }}
                />
            ) : (
                <article className="email-detail">
                    <header>
                        <h1>{email.data.subject || "(No subject)"}</h1>
                        <dl>
                            <div>
                                <dt>From</dt>
                                <dd>{email.data.sender || "Unknown sender"}</dd>
                            </div>
                            <div>
                                <dt>Received</dt>
                                <dd>
                                    <ReceivedTime value={email.data.received_at} />
                                </dd>
                            </div>
                            <div>
                                <dt>Template</dt>
                                <dd>
                                    {email.data.template_id === null ? (
                                        "No template assigned"
                                    ) : (
                                        <Link
                                            to={
                                                origin?.id === email.data.template_id
                                                    ? origin.href
                                                    : `/templates/${email.data.template_id}`
                                            }
                                        >
                                            Template {email.data.template_id}
                                        </Link>
                                    )}
                                </dd>
                            </div>
                        </dl>
                    </header>
                    <section aria-label="Email body" className="email-body">
                        {email.data.body || "This email has no body."}
                    </section>
                </article>
            )}
        </>
    );
}
