import { useEffect, useState } from "react";
import { useIsMutating } from "@tanstack/react-query";
import { useSync } from "./sync";
import { reduced } from "./ui";
import { AccountSetup } from "./components/AccountSetup";
import { SyncStatus } from "./components/SyncStatus";
import { ThemeToggle } from "./components/ThemeToggle";

export default function App() {
  const [phase, setPhase] = useState<"center" | "glide" | "setup">("center");
  const [handoff, setHandoff] = useState(false);
  const [notice, setNotice] = useState("");
  const sync = useSync();
  const accountBusy = useIsMutating() > 0;
  const ready = sync.pipeline.data?.state === "ready" && !sync.pipeline.isError;
  useEffect(() => {
    const start = window.setTimeout(
      () => setPhase(reduced() ? "setup" : "glide"),
      2000,
    );
    const finish = window.setTimeout(
      () => setPhase("setup"),
      reduced() ? 2000 : 2700,
    );
    return () => {
      clearTimeout(start);
      clearTimeout(finish);
    };
  }, []);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 2200);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (
        (event.metaKey || event.ctrlKey) &&
        event.key === "Enter" &&
        ready &&
        !accountBusy &&
        phase === "setup"
      ) {
        event.preventDefault();
        setHandoff(true);
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [ready, phase, accountBusy]);
  return (
    <main className={`app phase-${phase}`}>
      <ThemeToggle />
      {handoff ? (
        <section className="handoff" aria-labelledby="handoff-title">
          <h1
            id="handoff-title"
            tabIndex={-1}
            ref={(element) => element?.focus()}
          >
            Template review is coming next
          </h1>
          <p className="helper">
            {sync.pipeline.data?.templateCount === 0
              ? "No new email templates were found in this sync."
              : "Your emails are processed and your accounts are saved."}
          </p>
          <button
            className="button secondary"
            onClick={() => setHandoff(false)}
          >
            Back to accounts
          </button>
        </section>
      ) : (
        <>
          {phase === "setup" && <AccountSetup onNotice={setNotice} />}
          <SyncStatus
            phase={phase}
            sync={sync}
            accountBusy={accountBusy}
            onSeeTemplates={() => setHandoff(true)}
          />
        </>
      )}
      <div
        className={`toast ${notice ? "visible" : ""}`}
        role="status"
        aria-live="polite"
      >
        {notice}
      </div>
    </main>
  );
}
