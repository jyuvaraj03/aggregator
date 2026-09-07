import { useEffect } from "react";
import { Link, Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { EmailsScreen } from "../features/emails/EmailsScreen";
import { EmailDetailScreen } from "../features/emails/EmailDetailScreen";
import { TemplatesScreen } from "../features/templates/TemplatesScreen";
import { TemplateDetailScreen } from "../features/templates/TemplateDetailScreen";

export function App() {
    const { pathname } = useLocation();
    useEffect(() => {
        const title = pathname.startsWith("/emails/")
            ? "Email detail"
            : pathname.startsWith("/templates/")
              ? "Template detail"
              : pathname === "/templates"
                ? "Templates"
                : pathname === "/emails" || pathname === "/"
                  ? "Emails"
                  : "Page not found";
        document.title = `${title} · Aggregator`;
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
                    <nav className="app-nav" aria-label="Main navigation">
                        <NavLink to="/emails">Emails</NavLink>
                        <NavLink to="/templates">Templates</NavLink>
                    </nav>
                </div>
            </header>
            <main id="main" tabIndex={-1}>
                <Routes>
                    <Route path="/" element={<Navigate to="/emails" replace />} />
                    <Route path="/emails" element={<EmailsScreen />} />
                    <Route path="/emails/:emailId" element={<EmailDetailScreen />} />
                    <Route path="/templates" element={<TemplatesScreen />} />
                    <Route path="/templates/:templateId" element={<TemplateDetailScreen />} />
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
