import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ErrorState, ReceivedTime } from "../../components/shared";
import { errorMessage } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";
import {
    approveFieldParsers,
    fieldParserOptions,
    generateFieldParsers,
    saveFieldParsers,
    templateKeys,
    type FieldParserSet,
    type FieldParserSnapshot,
} from "./queries";

type TemplateDetail = components["schemas"]["TemplateDetailResponse"];
type FieldName = keyof FieldParserSet;
type ParserConfiguration = NonNullable<FieldParserSet[FieldName]>;
type ExtractedParser = Extract<ParserConfiguration, { rule: "extracted" }>;
type ParserDraft = Record<FieldName, ParserConfiguration | null>;

const fields: readonly { name: FieldName; label: string; description: string }[] = [
    { name: "amount", label: "Amount", description: "The transaction amount without formatting." },
    {
        name: "currency_code",
        label: "Currency code",
        description: "The currency symbol or code shown in the message.",
    },
    { name: "payee", label: "Payee", description: "The merchant or transfer counterparty." },
    {
        name: "description",
        label: "Description",
        description: "A short description of the transaction.",
    },
    {
        name: "transaction_date",
        label: "Transaction date",
        description: "A complete date that can be parsed unambiguously.",
    },
    {
        name: "account_hint",
        label: "Account hint",
        description: "A masked number or label identifying the account.",
    },
    {
        name: "is_credit",
        label: "Credit or debit",
        description: "A value that resolves to true for credit or false for debit.",
    },
];
const fieldNames = fields.map((field) => field.name);

function cloneConfiguration(configuration: ParserConfiguration | null | undefined) {
    if (!configuration) return null;
    if (configuration.rule === "extracted") {
        return { ...configuration, parameter_indices: [...configuration.parameter_indices] };
    }
    return { ...configuration };
}

function normalizeParsers(parsers: FieldParserSet): ParserDraft {
    return Object.fromEntries(
        fieldNames.map((name) => [name, cloneConfiguration(parsers[name])]),
    ) as ParserDraft;
}

function statusLabel(status: FieldParserSnapshot["field_parser_status"]) {
    if (status === "approved") return "Approved";
    if (status === "needs_review") return "Needs review";
    return "Needs generation";
}

function draftIsValid(draft: ParserDraft) {
    return fieldNames.every((name) => {
        const parser = draft[name];
        return parser?.rule !== "extracted" || parser.parameter_indices.length > 0;
    });
}

function draftIsComplete(draft: ParserDraft) {
    return fieldNames.every((name) => draft[name] !== null) && draftIsValid(draft);
}

function resolveValue(
    parser: ParserConfiguration | null,
    parameters: FieldParserSnapshot["parameters"],
) {
    if (!parser) return { state: "unconfigured", value: null };
    if (parser.rule === "missing") return { state: "missing", value: null };
    if (parser.rule === "constant") return { state: "value", value: parser.constant_value };
    return {
        state: "value",
        value: parser.parameter_indices
            .map((index) => parameters.find((parameter) => parameter.index === index)?.value ?? "")
            .join(" "),
    };
}

function PreviewValue({
    parser,
    parameters,
}: {
    parser: ParserConfiguration | null;
    parameters: FieldParserSnapshot["parameters"];
}) {
    const resolved = resolveValue(parser, parameters);
    if (resolved.state === "unconfigured") {
        return <span className="preview-placeholder">Not configured</span>;
    }
    if (resolved.state === "missing") {
        return <span className="preview-placeholder">Missing by design</span>;
    }
    return <span>{resolved.value || "Empty value"}</span>;
}

function ParameterEditor({
    field,
    parser,
    parameters,
    disabled,
    onChange,
}: {
    field: FieldName;
    parser: ExtractedParser;
    parameters: FieldParserSnapshot["parameters"];
    disabled: boolean;
    onChange: (parser: ParserConfiguration) => void;
}) {
    const selected = parser.parameter_indices;
    const available = parameters.filter((parameter) => !selected.includes(parameter.index));

    function move(index: number, offset: -1 | 1) {
        const position = selected.indexOf(index);
        const destination = position + offset;
        if (position < 0 || destination < 0 || destination >= selected.length) return;
        const next = [...selected];
        [next[position], next[destination]] = [next[destination]!, next[position]!];
        onChange({ rule: "extracted", parameter_indices: next });
    }

    return (
        <div className="parameter-editor">
            <span className="subfield-label">Join parameters in this order</span>
            {selected.length ? (
                <ol className="selected-parameters">
                    {selected.map((index, position) => {
                        const parameter = parameters.find((item) => item.index === index);
                        return (
                            <li key={index}>
                                <span className="parameter-index">P{index + 1}</span>
                                <span className="selected-parameter-value">
                                    {parameter?.value ?? "No example value"}
                                </span>
                                <span className="parameter-actions">
                                    <button
                                        className="secondary compact"
                                        type="button"
                                        disabled={disabled || position === 0}
                                        onClick={() => move(index, -1)}
                                    >
                                        Earlier
                                    </button>
                                    <button
                                        className="secondary compact"
                                        type="button"
                                        disabled={disabled || position === selected.length - 1}
                                        onClick={() => move(index, 1)}
                                    >
                                        Later
                                    </button>
                                    <button
                                        className="secondary compact"
                                        type="button"
                                        disabled={disabled}
                                        onClick={() =>
                                            onChange({
                                                rule: "extracted",
                                                parameter_indices: selected.filter(
                                                    (selectedIndex) => selectedIndex !== index,
                                                ),
                                            })
                                        }
                                    >
                                        Remove
                                    </button>
                                </span>
                            </li>
                        );
                    })}
                </ol>
            ) : (
                <p className="field-guidance error">Choose at least one source parameter.</p>
            )}
            {available.length > 0 && (
                <div className="add-parameter">
                    <label htmlFor={field + "-parameter"}>Add source parameter</label>
                    <select
                        id={field + "-parameter"}
                        value=""
                        disabled={disabled}
                        onChange={(event) => {
                            if (!event.target.value) return;
                            onChange({
                                rule: "extracted",
                                parameter_indices: [...selected, Number(event.target.value)],
                            });
                        }}
                    >
                        <option value="">Choose a parameter…</option>
                        {available.map((parameter) => (
                            <option key={parameter.index} value={parameter.index}>
                                P{parameter.index + 1} · {parameter.mask_name} ·{" "}
                                {parameter.value ?? "No example value"}
                            </option>
                        ))}
                    </select>
                </div>
            )}
        </div>
    );
}

function FieldEditor({
    field,
    label,
    description,
    parser,
    parameters,
    disabled,
    onChange,
}: {
    field: FieldName;
    label: string;
    description: string;
    parser: ParserConfiguration | null;
    parameters: FieldParserSnapshot["parameters"];
    disabled: boolean;
    onChange: (parser: ParserConfiguration | null) => void;
}) {
    return (
        <fieldset className="parser-field" disabled={disabled}>
            <legend>{label}</legend>
            <p>{description}</p>
            <div className="parser-rule-field">
                <label htmlFor={field + "-rule"}>Rule</label>
                <select
                    id={field + "-rule"}
                    value={parser?.rule ?? "unconfigured"}
                    onChange={(event) => {
                        const rule = event.target.value;
                        if (rule === "extracted") {
                            onChange({ rule: "extracted", parameter_indices: [] });
                        } else if (rule === "constant") {
                            onChange({ rule: "constant", constant_value: "" });
                        } else if (rule === "missing") {
                            onChange({ rule: "missing" });
                        } else {
                            onChange(null);
                        }
                    }}
                >
                    <option value="unconfigured">Not configured</option>
                    <option value="extracted">Extract from email</option>
                    <option value="constant">Use a fixed value</option>
                    <option value="missing">Always missing</option>
                </select>
            </div>
            {parser?.rule === "constant" && (
                <div className="constant-field">
                    <label htmlFor={field + "-constant"}>Fixed value</label>
                    <input
                        id={field + "-constant"}
                        value={parser.constant_value}
                        onChange={(event) =>
                            onChange({ rule: "constant", constant_value: event.target.value })
                        }
                    />
                </div>
            )}
            {parser?.rule === "extracted" && (
                <ParameterEditor
                    field={field}
                    parser={parser}
                    parameters={parameters}
                    disabled={disabled}
                    onChange={onChange}
                />
            )}
            {parser?.rule === "missing" && (
                <p className="field-guidance">This field will be stored without a value.</p>
            )}
        </fieldset>
    );
}

export function FieldParserReview({
    template,
    emailHref,
}: {
    template: TemplateDetail;
    emailHref: (emailId: number) => string;
}) {
    const snapshot = useQuery(fieldParserOptions(template.id));
    const queryClient = useQueryClient();
    const [draft, setDraft] = useState<ParserDraft | null>(null);
    const [saved, setSaved] = useState<ParserDraft | null>(null);
    const [confirmingGeneration, setConfirmingGeneration] = useState(false);
    const dirty = Boolean(draft && saved && JSON.stringify(draft) !== JSON.stringify(saved));

    useEffect(() => {
        document.title = "Review parser · Aggregator";
    }, []);

    useEffect(() => {
        if (!snapshot.data || draft) return;
        const initial = normalizeParsers(snapshot.data.parsers);
        setDraft(initial);
        setSaved(initial);
    }, [draft, snapshot.data]);

    useEffect(() => {
        if (!dirty) return;
        const beforeUnload = (event: BeforeUnloadEvent) => event.preventDefault();
        const blockLinks = (event: MouseEvent) => {
            if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey)
                return;
            const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
            if (!(link instanceof HTMLAnchorElement)) return;
            if (window.confirm("Discard your unsaved parser changes?")) return;
            event.preventDefault();
            event.stopPropagation();
        };
        window.addEventListener("beforeunload", beforeUnload);
        document.addEventListener("click", blockLinks, true);
        return () => {
            window.removeEventListener("beforeunload", beforeUnload);
            document.removeEventListener("click", blockLinks, true);
        };
    }, [dirty]);

    function adoptSnapshot(next: FieldParserSnapshot) {
        const nextDraft = normalizeParsers(next.parsers);
        setDraft(nextDraft);
        setSaved(nextDraft);
        queryClient.setQueryData(
            [...templateKeys.all, "detail", template.id, "field-parsers"],
            next,
        );
        queryClient.setQueryData<TemplateDetail>(
            [...templateKeys.all, "detail", template.id],
            (current) =>
                current ? { ...current, field_parser_status: next.field_parser_status } : current,
        );
        void queryClient.invalidateQueries({
            queryKey: [...templateKeys.all, "list"],
            refetchType: "none",
        });
    }

    const save = useMutation({ mutationFn: saveFieldParsers, onSuccess: adoptSnapshot });
    const approve = useMutation({ mutationFn: approveFieldParsers, onSuccess: adoptSnapshot });
    const generate = useMutation({
        mutationFn: generateFieldParsers,
        onSuccess: (next) => {
            setConfirmingGeneration(false);
            adoptSnapshot(next);
        },
    });
    const busy = save.isPending || approve.isPending || generate.isPending;

    const preview = useMemo(
        () => (draft ? fields.map((field) => ({ ...field, parser: draft[field.name] })) : []),
        [draft],
    );

    function updateField(name: FieldName, parser: ParserConfiguration | null) {
        save.reset();
        approve.reset();
        setDraft((current) => (current ? { ...current, [name]: parser } : current));
    }

    async function runGeneration() {
        try {
            await generate.mutateAsync(template.id);
        } catch {
            // The mutation error is rendered without discarding the current parser.
        }
    }

    if (snapshot.isPending || !draft) {
        return (
            <div className="parser-loading" role="status">
                <span />
                <span />
                <span />
                Loading field parser…
            </div>
        );
    }
    if (snapshot.isError) {
        return (
            <ErrorState
                error={snapshot.error}
                retry={() => {
                    void snapshot.refetch();
                }}
            />
        );
    }

    const data = snapshot.data;
    const hasConfiguredParser = fieldNames.some((name) => saved?.[name] !== null);
    const validDraft = draftIsValid(draft);
    const completeDraft = draftIsComplete(draft);
    const approved = data.field_parser_status === "approved" && !dirty;

    return (
        <>
            <header className="page-heading parser-page-heading">
                <div>
                    <h1>Template {template.id}</h1>
                    <p>Review how one matching email becomes a structured transaction.</p>
                </div>
                <span className={"parser-status-badge " + data.field_parser_status}>
                    {statusLabel(data.field_parser_status)}
                </span>
            </header>

            <section className="parser-toolbar" aria-labelledby="parser-toolbar-heading">
                <div>
                    <h2 id="parser-toolbar-heading">Field parser</h2>
                    <p>
                        {approved
                            ? "This parser is approved for transaction extraction."
                            : "Generated rules stay out of extraction until you approve them."}
                    </p>
                </div>
                <button
                    className="secondary"
                    type="button"
                    disabled={busy}
                    onClick={() => {
                        if (hasConfiguredParser || dirty) setConfirmingGeneration(true);
                        else void runGeneration();
                    }}
                >
                    {generate.isPending
                        ? "Generating…"
                        : hasConfiguredParser
                          ? "Regenerate parser"
                          : "Generate parser"}
                </button>
            </section>

            {confirmingGeneration && !generate.isPending && (
                <div className="replace-confirmation" role="alert">
                    <div>
                        <strong>Replace this parser?</strong>
                        <p>
                            Regeneration replaces saved rules, discards unsaved changes, and
                            requires approval again.
                        </p>
                    </div>
                    <div className="confirmation-actions">
                        <button
                            className="secondary"
                            type="button"
                            onClick={() => setConfirmingGeneration(false)}
                        >
                            Cancel
                        </button>
                        <button type="button" onClick={() => void runGeneration()}>
                            Replace parser
                        </button>
                    </div>
                </div>
            )}
            {generate.isPending && (
                <p className="operation-message" role="status">
                    Generating a new parser. Current rules remain until it succeeds.
                </p>
            )}
            {generate.isError && (
                <p className="operation-message error" role="alert">
                    {errorMessage(generate.error)} Your existing parser was not changed.
                </p>
            )}
            {generate.isSuccess && (
                <p className="operation-message success" role="status">
                    Parser generated. Review the draft before approving it.
                </p>
            )}

            <form
                className="parser-workbench"
                onSubmit={async (event) => {
                    event.preventDefault();
                    if (!dirty || !validDraft || busy) return;
                    try {
                        await save.mutateAsync({ id: template.id, parsers: draft });
                    } catch {
                        // The mutation error is rendered below.
                    }
                }}
            >
                <div className="parser-main-column">
                    <section className="parser-source" aria-labelledby="source-heading">
                        <div className="parser-section-heading">
                            <div>
                                <h2 id="source-heading">Source example</h2>
                                <p>The numbered values are available to extracted rules.</p>
                            </div>
                            {template.example && (
                                <Link to={emailHref(template.example.id)}>Open full email</Link>
                            )}
                        </div>
                        <pre className="parser-template-text">{data.text}</pre>
                        {data.parameters.length ? (
                            <ol className="source-parameters">
                                {data.parameters.map((parameter) => (
                                    <li key={parameter.index}>
                                        <span className="parameter-index">
                                            P{parameter.index + 1}
                                        </span>
                                        <span className="parameter-mask">
                                            {parameter.mask_name}
                                        </span>
                                        <strong>{parameter.value ?? "No example value"}</strong>
                                    </li>
                                ))}
                            </ol>
                        ) : (
                            <p className="source-empty">
                                This template has no variable parameters. Use fixed or missing
                                rules.
                            </p>
                        )}
                        {template.example && (
                            <details className="example-context">
                                <summary>Show example email context</summary>
                                <dl>
                                    <div>
                                        <dt>Subject</dt>
                                        <dd>{template.example.subject || "(No subject)"}</dd>
                                    </div>
                                    <div>
                                        <dt>From</dt>
                                        <dd>{template.example.sender || "Unknown sender"}</dd>
                                    </div>
                                    <div>
                                        <dt>Received</dt>
                                        <dd>
                                            <ReceivedTime value={template.example.received_at} />
                                        </dd>
                                    </div>
                                </dl>
                                <div className="email-body">{template.example.body}</div>
                            </details>
                        )}
                    </section>

                    <section className="parser-editor" aria-labelledby="rules-heading">
                        <div className="parser-section-heading">
                            <div>
                                <h2 id="rules-heading">Field rules</h2>
                                <p>Configure every field, including values not present.</p>
                            </div>
                            <span className="configured-count">
                                {fieldNames.filter((name) => draft[name] !== null).length} of{" "}
                                {fieldNames.length} configured
                            </span>
                        </div>
                        <div className="parser-fields">
                            {fields.map((field) => (
                                <FieldEditor
                                    key={field.name}
                                    field={field.name}
                                    label={field.label}
                                    description={field.description}
                                    parser={draft[field.name]}
                                    parameters={data.parameters}
                                    disabled={busy}
                                    onChange={(parser) => updateField(field.name, parser)}
                                />
                            ))}
                        </div>
                    </section>
                </div>

                <aside className="parser-preview" aria-labelledby="preview-heading">
                    <div className="preview-heading-row">
                        <h2 id="preview-heading">Resolved transaction</h2>
                        {dirty && <span className="draft-indicator">Unsaved</span>}
                    </div>
                    {data.example_email_id ? (
                        <dl className="transaction-preview">
                            {preview.map((field) => (
                                <div key={field.name}>
                                    <dt>{field.label}</dt>
                                    <dd>
                                        <PreviewValue
                                            parser={field.parser}
                                            parameters={data.parameters}
                                        />
                                    </dd>
                                </div>
                            ))}
                        </dl>
                    ) : (
                        <p className="preview-empty">
                            Add a matching email before reviewing or approving this parser.
                        </p>
                    )}

                    <div className="review-actions">
                        {!validDraft && (
                            <p className="error">Every extracted rule needs a source parameter.</p>
                        )}
                        {validDraft && !completeDraft && (
                            <p>Configure all seven fields before approval.</p>
                        )}
                        {dirty && completeDraft && <p>Save this draft before approving it.</p>}
                        {approved && (
                            <p className="approval-note success">
                                Approved and eligible once an account is assigned.
                            </p>
                        )}
                        {save.isError && (
                            <p className="error" role="alert">
                                {errorMessage(save.error)}
                            </p>
                        )}
                        {approve.isError && (
                            <p className="error" role="alert">
                                {errorMessage(approve.error)}
                            </p>
                        )}
                        {save.isSuccess && !dirty && !approved && (
                            <p className="success" role="status">
                                Draft saved. Check the preview, then approve it.
                            </p>
                        )}
                        {approve.isSuccess && (
                            <p className="success" role="status">
                                Parser approved for transaction extraction.
                            </p>
                        )}
                        <button type="submit" disabled={!dirty || !validDraft || busy}>
                            {save.isPending ? "Saving…" : "Save draft"}
                        </button>
                        <button
                            className="secondary approve-button"
                            type="button"
                            disabled={dirty || !completeDraft || busy || approved}
                            onClick={async () => {
                                try {
                                    await approve.mutateAsync(template.id);
                                } catch {
                                    // The mutation error is rendered above.
                                }
                            }}
                        >
                            {approve.isPending
                                ? "Approving…"
                                : approved
                                  ? "Approved"
                                  : "Approve parser"}
                        </button>
                    </div>
                </aside>
            </form>
        </>
    );
}
