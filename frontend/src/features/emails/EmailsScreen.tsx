import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { errorMessage } from "../../lib/api/client";
import { emailKeys, emailPageOptions, syncEmails } from "./queries";
import { ErrorState, Pagination, readPage } from "../../components/shared";
import { EmailRows } from "../../components/EmailRows";

export function EmailsScreen() {
    const [search, setSearch] = useSearchParams();
    const page = readPage(search.get("page"));
    const emails = useQuery(emailPageOptions(page));
    const client = useQueryClient();
    const [fromDate, setFromDate] = useState("");
    const submitting = useRef(false);
    const sync = useMutation({
        mutationFn: syncEmails,
        retry: false,
        onSuccess: async () => {
            // Cancel old reads before invalidating so pre-sync results cannot overwrite new data.
            await client.cancelQueries({ queryKey: emailKeys.all });
            await client.invalidateQueries({ queryKey: emailKeys.all, refetchType: "none" });
            setSearch({ page: "1" });
            await client.refetchQueries({ queryKey: [...emailKeys.all, "list", 1] });
        },
    });

    return (
        <>
            <header className="page-heading">
                <h1>Emails</h1>
                <p>Sync your mailbox. Inspect what’s stored.</p>
            </header>
            <section className="sync-panel" aria-labelledby="sync-heading">
                <div>
                    <h2 id="sync-heading">Sync emails</h2>
                    <p>Pull messages from your configured Gmail label, starting on a date.</p>
                </div>
                <form
                    onSubmit={async (event) => {
                        event.preventDefault();
                        if (submitting.current || !fromDate) return;
                        submitting.current = true;
                        try {
                            await sync.mutateAsync({ from_date: fromDate });
                        } catch {
                            /* The mutation error is rendered below; retain the user's inputs. */
                        } finally {
                            submitting.current = false;
                        }
                    }}
                >
                    <div className="field">
                        <label htmlFor="from-date">Start date</label>
                        <input
                            id="from-date"
                            type="date"
                            required
                            value={fromDate}
                            disabled={sync.isPending}
                            onChange={(event) => setFromDate(event.target.value)}
                        />
                    </div>
                    <button type="submit" disabled={sync.isPending || !fromDate}>
                        {sync.isPending ? "Syncing…" : "Sync emails"}
                    </button>
                </form>
                {sync.isPending && (
                    <p role="status">Pulling and storing emails. This may take a moment.</p>
                )}
                {sync.isError && (
                    <p className="error sync-message" role="alert">
                        {errorMessage(sync.error)}
                    </p>
                )}
                {sync.isSuccess && (
                    <p className="success sync-message" role="status">
                        <strong>Sync complete.</strong> {sync.data.pulled} pulled ·{" "}
                        {sync.data.inserted} inserted · {sync.data.already_stored} already stored
                        <span className="result-note">
                            Template mining and parser generation are continuing in the background.{" "}
                            <Link to="/templates">View templates</Link>
                        </span>
                    </p>
                )}
            </section>
            <section
                className="email-list"
                aria-labelledby="stored-heading"
                aria-busy={emails.isFetching}
            >
                <div className="section-heading">
                    <div>
                        <h2 id="stored-heading">All stored emails</h2>
                        <p>Includes emails from every sync.</p>
                    </div>
                    {emails.data && (
                        <span className="total">{emails.data.total.toLocaleString()} total</span>
                    )}
                </div>
                {emails.isPending && (
                    <div className="state" role="status">
                        Loading emails…
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
                            <EmailRows
                                emails={emails.data.items}
                                href={(id) => `/emails/${id}?page=${page}`}
                            />
                        ) : (
                            <div className="state">
                                <h3>
                                    {emails.data.total === 0
                                        ? "No emails stored yet"
                                        : "No emails on this page"}
                                </h3>
                                <p>
                                    {emails.data.total === 0
                                        ? "Choose a start date above, then sync your emails."
                                        : "Return to the first page to browse stored emails."}
                                </p>
                                {page > 1 && <Link to="/emails?page=1">Go to first page</Link>}
                            </div>
                        )}
                        <Pagination
                            page={page}
                            totalPages={emails.data.total_pages}
                            label="Email pages"
                            onPage={(next) => setSearch({ page: String(next) })}
                        />
                    </>
                )}
            </section>
        </>
    );
}
