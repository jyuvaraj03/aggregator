# Syncing and Add your accounts

Implemented surface: Vite + React + TypeScript, TanStack Query, plain CSS, local FastAPI API. Source: `frontend/src/App.tsx`, `components/`, `styles.css`, `tokens.css`, and `colors.ts`.

Visual authority: `docs/frontend-reference/Template Review — mockup.html` and `template-review-spec.md`, especially Syncing, Add your accounts, keyboard, and account motion. Preserve the supplied composition and material language; `DESIGN.md` records effective implemented values.

Scope: initial syncing introduction; account loading/error states; create, edit, remove, duplicate validation and pending states; named theme menu; persistent theme toggle; backend-driven sync status, ready action, retry/restart, and an explicit deferred-review handoff. The 10-second mockup readiness timer is replaced by real backend state. Template review, templates-found ripple, clipboard, parser tag editing, account/move sheets, and completion screens are deferred; their presence in the reference is not evidence of implementation.

Intentional reference adaptations: stronger secondary/placeholder/muted/key-chip contrast; mobile horizontal saved-account strip and flowing footer; flowing footer for desktop heights at or below 650px, preventing ready/error actions from overlapping an editing form. Keep required looping shine and spring easing while honoring reduced motion.

Review evidence: `.impeccable/review/desktop.png`, `desktop-dark.png`, `mobile.png`, `mobile-dark.png`, `short-desktop-ready.png`, `short-desktop-editing.png`, and `short-desktop-error.png`. Review found a short-desktop footer overlap; the final fix moves the footer into document flow. Final reviewer verdict: ship for that fix.
