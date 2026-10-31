import { useState } from "react";
import type { useSync } from "../sync";
import { message, modKey } from "../ui";
import { KeyHint } from "./KeyHint";

interface SyncStatusProps {
  phase: "center" | "glide" | "setup";
  sync: ReturnType<typeof useSync>;
  accountBusy: boolean;
  onSeeTemplates: () => void;
}

export function SyncStatus({
  phase,
  sync,
  accountBusy,
  onSeeTemplates,
}: SyncStatusProps) {
  const [restartError, setRestartError] = useState("");
  const [restarting, setRestarting] = useState(false);
  const ready = sync.pipeline.data?.state === "ready" && !sync.pipeline.isError;
  const failed = sync.pipeline.data?.state === "failed";
  const syncError = sync.session.error ?? sync.pipeline.error;
  const errorText =
    restartError ||
    (syncError ? message(syncError) : failed ? sync.pipeline.data!.label : "");
  async function restart() {
    setRestarting(true);
    setRestartError("");
    try {
      await sync.restart();
    } catch (error) {
      setRestartError(message(error));
    } finally {
      setRestarting(false);
    }
  }
  return (
    <div
      className={`sync-status ${phase !== "setup" ? "sync-intro" : ""}`}
      role="status"
      aria-live="polite"
    >
      {phase !== "setup" ? (
        <h2 className="shine">Syncing emails…</h2>
      ) : errorText ? (
        <div className="sync-error">
          <p>{errorText}</p>
          <button
            className="button secondary"
            disabled={
              restarting || sync.session.isFetching || sync.pipeline.isFetching
            }
            onClick={() => (failed ? void restart() : void sync.retry())}
          >
            {restarting
              ? "Restarting…"
              : failed
                ? "Restart sync"
                : "Retry checking"}
          </button>
        </div>
      ) : ready ? (
        <button
          className="button primary see-templates"
          disabled={accountBusy}
          onClick={onSeeTemplates}
        >
          <span>See templates</span>
          <span className="keys">
            <KeyHint>{modKey}</KeyHint>
            <KeyHint>↵</KeyHint>
          </span>
        </button>
      ) : (
        <h2 className="shine">
          {sync.pipeline.data?.label ?? "Syncing emails…"}
        </h2>
      )}
    </div>
  );
}
