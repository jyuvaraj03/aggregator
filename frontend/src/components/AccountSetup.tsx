import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteAccount, listAccounts, saveAccount, type Account } from "../api";
import { nextColor } from "../colors";
import { message, modKey, reduced } from "../ui";
import { AccountCard } from "./AccountCard";
import { AccountStack, type AccountStackHandle } from "./AccountStack";
import { KeyHint } from "./KeyHint";
import { ThemePicker } from "./ThemePicker";

export function AccountSetup({
  onNotice,
}: {
  onNotice: (text: string) => void;
}) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["accounts"],
    queryFn: ({ signal }) => listAccounts(signal),
  });
  const accounts = query.data ?? [];
  const [editing, setEditing] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [chosenColor, setChosenColor] = useState<number | null>(null);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const preview = useRef<HTMLDivElement>(null);
  const stack = useRef<AccountStackHandle>(null);
  const color = chosenColor ?? nextColor(accounts);
  const selected = accounts.find((account) => account.id === editing);

  function reset() {
    setEditing(null);
    setName("");
    setChosenColor(null);
    setError("");
    input.current?.focus();
  }
  function select(account: Account) {
    setEditing(account.id);
    setName(account.name);
    setChosenColor(account.color);
    setError("");
    requestAnimationFrame(() => {
      input.current?.focus();
      input.current?.setSelectionRange(
        account.name.length,
        account.name.length,
      );
    });
  }
  const save = useMutation({
    mutationFn: ({
      id,
      name,
      color,
    }: {
      id: number | null;
      name: string;
      color: number;
    }) => saveAccount(id, name, color),
    onSuccess: (account, variables) => {
      if (variables.id === null && preview.current)
        stack.current?.prepareAddition(
          account.id,
          preview.current.getBoundingClientRect(),
        );
      client.setQueryData<Account[]>(["accounts"], (previous) =>
        [
          ...(previous ?? []).filter((item) => item.id !== account.id),
          account,
        ].sort((a, b) => a.id - b.id),
      );
      reset();
      onNotice(`${variables.id === null ? "Added" : "Saved"} ${account.name}`);
      void client.invalidateQueries({ queryKey: ["accounts"] });
    },
    onSettled: () => requestAnimationFrame(() => input.current?.focus()),
    onError: (cause) => {
      setError(message(cause));
      input.current?.focus();
    },
  });
  const remove = useMutation({
    mutationFn: deleteAccount,
    onSuccess: async (_, id) => {
      await stack.current?.animateRemoval(id);
      const removed = accounts.find((account) => account.id === id);
      client.setQueryData<Account[]>(["accounts"], (previous) =>
        previous?.filter((account) => account.id !== id),
      );
      reset();
      onNotice(`Removed ${removed?.name ?? "account"}`);
      void client.invalidateQueries({ queryKey: ["accounts"] });
    },
    onSettled: () => requestAnimationFrame(() => input.current?.focus()),
    onError: (cause) => setError(message(cause)),
  });
  const busy = save.isPending || remove.isPending;
  useEffect(() => {
    if (query.isSuccess) input.current?.focus({ preventScroll: true });
  }, [query.isSuccess]);
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (busy) return;
      if (
        event.key === "Escape" &&
        !(event.target as HTMLElement).closest(".swatches")
      ) {
        event.preventDefault();
        reset();
      }
      if (
        (event.metaKey || event.ctrlKey) &&
        event.key === "/" &&
        editing !== null
      ) {
        event.preventDefault();
        remove.mutate(editing);
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Enter an account name.");
      input.current?.focus();
      return;
    }
    if (trimmed.length > 40) {
      setError("Use 40 characters or fewer.");
      return;
    }
    const duplicate = accounts.find(
      (account) =>
        account.id !== editing &&
        account.name.toLowerCase() === trimmed.toLowerCase(),
    );
    if (duplicate) {
      setError(`${duplicate.name} already exists`);
      input.current?.focus();
      return;
    }
    setError("");
    save.mutate({ id: editing, name: trimmed, color });
  }
  return (
    <>
      <AccountStack
        ref={stack}
        accounts={accounts}
        selectedId={editing}
        busy={busy}
        onSelect={select}
        onAdd={reset}
        previewRef={preview}
      />
      <section className="setup" aria-labelledby="setup-title">
        <h1 id="setup-title">Add your accounts</h1>
        <p className="helper">
          Add each bank account, debit card and credit card on its own, so you
          can tell their transactions apart.
        </p>
        {query.isPending ? (
          <p className="account-loading" role="status">
            Loading your accounts…
          </p>
        ) : query.isError ? (
          <div className="inline-error" role="alert">
            <p>{message(query.error)}</p>
            <button
              className="text-button"
              onClick={() => void query.refetch()}
            >
              Retry loading accounts
            </button>
          </div>
        ) : (
          <form className="editor" onSubmit={submit} aria-busy={busy}>
            <div className="preview" ref={preview} key={editing ?? "new"}>
              <AccountCard name={name} color={color} />
            </div>
            <div className="editor-fields">
              <div className={`field name-field ${error ? "invalid" : ""}`}>
                <label className="field-label" htmlFor="account-name">
                  Account name
                </label>
                <div className="field-control">
                  <input
                    id="account-name"
                    ref={input}
                    value={name}
                    maxLength={40}
                    placeholder="Enter account name"
                    autoComplete="off"
                    disabled={busy}
                    aria-invalid={!!error}
                    aria-describedby={error ? "account-error" : undefined}
                    onChange={(event) => {
                      setName(event.target.value);
                      setError("");
                    }}
                  />
                  {name.length >= 30 && (
                    <span
                      className={`counter ${name.length >= 40 ? "full" : ""}`}
                      aria-live="polite"
                    >
                      {name.length}/40
                    </span>
                  )}
                </div>
              </div>
              <ThemePicker
                color={color}
                disabled={busy}
                onChange={(value) => {
                  setChosenColor(value);
                  if (!reduced())
                    preview.current?.animate(
                      [{ transform: "scale(.98)" }, { transform: "scale(1)" }],
                      { duration: 260, easing: "cubic-bezier(.34,1.45,.55,1)" },
                    );
                }}
              />
            </div>
            {error && (
              <p className="inline-error" role="alert" id="account-error">
                {error}
              </p>
            )}
            <button
              className="button primary"
              disabled={busy || !name.trim()}
              type="submit"
            >
              <span>
                {save.isPending
                  ? "Saving…"
                  : editing !== null
                    ? "Save changes"
                    : "Add account"}
              </span>
              <KeyHint>↵</KeyHint>
            </button>
            {editing !== null && (
              <button
                className="button danger"
                type="button"
                disabled={busy}
                onClick={() => remove.mutate(editing)}
              >
                <span>{remove.isPending ? "Removing…" : "Remove account"}</span>
                <span className="keys">
                  <KeyHint>{modKey}</KeyHint>
                  <KeyHint>/</KeyHint>
                </span>
              </button>
            )}
            <p className="editor-note">
              {selected
                ? `Editing ${selected.name}`
                : "You can add more accounts later, too."}
            </p>
          </form>
        )}
      </section>
    </>
  );
}
