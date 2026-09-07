import { Link } from "react-router-dom";
import type { components } from "../lib/api/schema";
import { ReceivedTime } from "./shared";

export function EmailRows({
    emails,
    href,
}: {
    emails: components["schemas"]["EmailSummary"][];
    href: (id: number) => string;
}) {
    return (
        <ul className="messages">
            {emails.map((email) => (
                <li key={email.id}>
                    <Link className="email-row" to={href(email.id)}>
                        <span className="email-copy">
                            <span className="sender">{email.sender || "Unknown sender"}</span>
                            <span className="subject">{email.subject || "(No subject)"}</span>
                        </span>
                        <ReceivedTime value={email.received_at} />
                        <svg className="chevron" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="m9 5 7 7-7 7" />
                        </svg>
                    </Link>
                </li>
            ))}
        </ul>
    );
}
