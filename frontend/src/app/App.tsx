import { useEffect } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { EmailsScreen } from "../features/emails/EmailsScreen";
import { EmailDetailScreen } from "../features/emails/EmailDetailScreen";

export function App() {
    const { pathname } = useLocation();
    useEffect(() => {
        document.title = `${pathname.startsWith("/emails/") ? "Email detail" : "Emails"} · Aggregator`;
        document.getElementById("main")?.focus();
    }, [pathname]);
    return (
        <>
            <a className="skip-link" href="#main">
                Skip to content
            </a>
            <header className="app-header">
                <div className="app-header-inner">
                    <Link className="brand" to="/emails">
                        Aggregator
                    </Link>
                    <span>Local email workspace</span>
                </div>
            </header>
            <main id="main" tabIndex={-1}>
                <Routes>
                    <Route path="/" element={<Navigate to="/emails" replace />} />
                    <Route path="/emails" element={<EmailsScreen />} />
                    <Route path="/emails/:emailId" element={<EmailDetailScreen />} />
                    <Route
                        path="*"
                        element={
                            <div className="state">
                                <h1>Page not found</h1>
                                <Link to="/emails">Go to emails</Link>
                            </div>
                        }
                    />
                </Routes>
            </main>
        </>
    );
}
