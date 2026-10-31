---
name: Aggregator
description: Cool neutral setup surfaces with tactile account cards.
colors:
  surface-page: "#f4f6f9"
  surface-paper: "#ffffff"
  border-card: "#dce0e7"
  border-input: "#e1e5eb"
  ink-body: "#333c49"
  ink-heading: "#505b6c"
  ink-muted: "#707989"
  ink-meta: "#707680"
  ink-placeholder: "#727c8b"
  action-primary: "#393a3e"
  action-primary-hover: "#2c2d30"
  action-primary-ink: "#ffffff"
  action-primary-disabled: "#c9cace"
  action-secondary: "#dadee6"
  action-secondary-hover: "#cfd4dd"
  action-secondary-ink: "#3a4352"
  action-danger: "#f2dde3"
  action-danger-hover: "#ecd0d9"
  action-danger-ink: "#c4162f"
  key-chip-primary: "#4a4b50"
  key-chip-primary-ink: "#d2d3d8"
  key-chip-secondary: "#ced3db"
  key-chip-danger: "#e6d1d8"
  key-chip-ink: "#5b6473"
  brand-blue: "#3b71c6"
  label-grey: "#e6e9ee"
  dark-surface-page: "#14171c"
  dark-surface-paper: "#22272e"
  dark-border-card: "#343b45"
  dark-border-input: "#3a414b"
  dark-ink-body: "#d3d8df"
  dark-ink-heading: "#c6cdd7"
  dark-ink-muted: "#a0a9b7"
  dark-ink-meta: "#9aa3b1"
  dark-ink-placeholder: "#a0a9b7"
  dark-action-primary: "#e8ebf0"
  dark-action-primary-hover: "#ffffff"
  dark-action-primary-ink: "#14171c"
  dark-action-primary-disabled: "#3a4049"
  dark-action-secondary: "#2a3038"
  dark-action-secondary-hover: "#353c46"
  dark-action-secondary-ink: "#d3d8df"
  dark-action-danger: "#36222a"
  dark-action-danger-hover: "#432830"
  dark-action-danger-ink: "#ff8b9c"
  dark-key-chip-primary: "#d0d5dc"
  dark-key-chip-primary-ink: "#4a5260"
  dark-key-chip-secondary: "#3a414b"
  dark-key-chip-danger: "#4b2c35"
  dark-key-chip-ink: "#aab2bf"
  dark-brand-blue: "#79a3e6"
  dark-label-grey: "#2a3038"
typography:
  headline:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "28px"
    lineHeight: "36px"
    fontWeight: 600
  title:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "20px"
    lineHeight: "28px"
    fontWeight: 600
  body:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "15px"
    lineHeight: "22px"
    fontWeight: 400
  control:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "17px"
    lineHeight: "24px"
    fontWeight: 600
  input:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "17px"
    lineHeight: "24px"
    fontWeight: 500
  card-name:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "18px"
    lineHeight: "24px"
    fontWeight: 500
  label:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "13px"
    lineHeight: "18px"
    fontWeight: 500
  small:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "13px"
    lineHeight: "18px"
    fontWeight: 400
rounded:
  xs: "6px"
  md: "12px"
  lg: "16px"
  pill: "999px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "6": "24px"
  "8": "32px"
  "12": "48px"
components:
  button-primary:
    backgroundColor: "{colors.action-primary}"
    textColor: "{colors.action-primary-ink}"
    typography: "{typography.control}"
    rounded: "{rounded.lg}"
    padding: "10px 12px 10px 20px"
    width: "100%"
  button-primary-hover:
    backgroundColor: "{colors.action-primary-hover}"
  button-secondary:
    backgroundColor: "{colors.action-secondary}"
    textColor: "{colors.action-secondary-ink}"
    typography: "{typography.control}"
    rounded: "{rounded.lg}"
    padding: "10px 12px 10px 20px"
    width: "100%"
  button-secondary-hover:
    backgroundColor: "{colors.action-secondary-hover}"
  button-danger:
    backgroundColor: "{colors.action-danger}"
    textColor: "{colors.action-danger-ink}"
    typography: "{typography.control}"
    rounded: "{rounded.lg}"
    padding: "10px 12px 10px 20px"
    width: "100%"
  button-danger-hover:
    backgroundColor: "{colors.action-danger-hover}"
  input:
    backgroundColor: "{colors.surface-paper}"
    textColor: "{colors.ink-body}"
    typography: "{typography.input}"
    rounded: "{rounded.lg}"
    padding: "0 14px"
---

# Design System: Aggregator

## Overview

**Creative North Star: "Account cards on a quiet canvas"**

The supplied Template Review mockup establishes the visual authority: a quiet, cool canvas, generous space, soft rounded controls, and account cards with visible material character. Preserve this world when extending the interface; the current implementation uses React with plain CSS, not a component-library theme.

This is a description of the implemented Syncing and Add your accounts surfaces, not a new identity. The name above summarizes the supplied reference rather than establishing a separate brand. See [the surface brief](.impeccable/surfaces/account-setup.md) for scope and reference differences.

**Key Characteristics:**

- Cool neutral surfaces and charcoal primary actions.
- Local Schibsted Grotesk, proportional figures, sentence case.
- Tabbed field labels, right-aligned key hints, patterned account cards.

## Colors

The primary action is charcoal in light mode and pale ink in dark mode; blue marks focus rather than dominating the page. Frontmatter records the effective cascade, with `dark-` counterparts applied by `html[data-theme="dark"]`.

- **Primary:** action-primary and its hover/ink roles distinguish the main action; secondary is a cool grey, danger a pink surface with red text.
- **Neutral:** surface-page is the cool canvas; surface-paper fills fields and menus. Heading, body, muted, meta, and placeholder inks form the hierarchy.
- **Focus:** brand-blue supplies the focus ring and caret. It is not a replacement primary-button fill.
- **Account identity:** the 20 named swatches in `frontend/src/colors.ts` belong to account cards, not global action semantics. Keep their established order and names.

Placeholder, muted, and primary key-chip text intentionally have stronger contrast than the original mockup. Keep the effective overrides in `styles.css`; source order matters. Secondary controls also follow the implemented, more legible treatment rather than a screenshot color sample.

## Typography

Use the bundled variable Schibsted Grotesk (400–900), with the frontmatter system fallbacks; no external font request. Keep proportional figures. The heading uses the headline role with slightly tight tracking (−0.01em); account names use the same tracking. Body is regular; labels and inputs are medium; headings and buttons are semibold. Setup notes and key hints use the small role. Stack card names become smaller on mobile (15/20px). Do not import the deferred review amount/display hierarchy into setup.

## Layout

The setup editor is a centered column (340px, max-width 100%) on an open canvas. Helper copy can extend to 380px, constrained by viewport gutters. The preview is 16:9. Fields use a flexible name column plus an 84px Theme column and a 10px gap. Buttons and fields have a minimum height of 52px; buttons may grow for content.

Desktop accounts overlap at the left edge in a scrollable vertical stack, partly off-canvas. Cards are 320×180px; their step clamps between 28px and 92px as count and viewport height change. Hover raises a card 10px; selection shifts it 24px right at the raised height. Main content reserves space for the bottom sync status.

At widths up to 767px, use a horizontal, scrollable account strip of 220px cards above the form, 24px page gutters, and a status/action footer in normal document flow. At desktop widths from 768px with height up to 650px, the status/action footer also flows below the editor, including editing and error states. Never pin it over form controls. The document supports a minimum width of 320px. The top-right theme toggle remains fixed (40px square).

## Elevation & Depth

Depth is selective: the page remains open and flat while cards carry material. Named account cards use a 135-degree gradient (base mixed 18% toward white, through base at 48%, to base mixed 38% toward black), translucent SVG patterns, and a name tinted 80% toward white. Eight patterns repeat by swatch index modulo eight. Unnamed/add cards use the frosted silver gradient, subtle tint, diagonal sheen, inset edge, and 10px backdrop blur. Dark mode lowers the sheen and edge intensity. Account-stack shadows separate overlaps; the color menu has a soft floating shadow. Exact shadow and motion values live in the sidecar and source CSS.

## Shapes

Use generous rounded controls and cards (lg), smaller key chips (xs), and pill toasts. Field labels join their field through a two-pixel border and an eight-pixel top-only corner. Theme swatches use nine-pixel corners; the sample uses ten-pixel corners. Preserve card clipping, but keep names to two wrapped lines and error text free to wrap.

## Components

- **Buttons:** left-aligned labels, right-hand key chips, primary/secondary/danger variants. Hover changes fill; press scales to 0.98. Pending operations disable affected controls and name the operation. Disabled primary uses its dedicated token and 0.7 opacity; other disabled buttons use 0.55 opacity.
- **Fields:** joined grey label tabs, paper fill, two-pixel border. Focus changes the field border; other controls show a blue two-pixel focus ring with four-pixel offset. Invalid name fields turn red and shake briefly, with a visible associated error message. The name counter appears at 30 characters and turns red at 40.
- **Theme menu:** a five-column, four-row swatch grid above the trigger, with named choices, a check mark, and selected outline. Opening focuses the selected swatch; arrows, Home/End, Enter/Space, and Escape work. Escape/selection restores trigger focus; outside pointer or focus closes it.
- **Account stack:** button cards select the account for editing, using pressed state and an accessible name. The final silver card resets to a new account. Preview names fade from silver to the selected patterned color as the user types.
- **Sync status and ready action:** center text glides to the footer before setup appears. Status is announced politely; errors have retry/restart controls. Readiness comes from backend state. See templates currently opens an explicit deferred-review handoff.
- **Toasts:** a bottom-center primary-colored pill confirms added, saved, or removed accounts for 2.2 seconds.

**Motion exceptions:** the supplied reference explicitly requires looping text shine (2.2s), the ready button light sweep (2.6s), and spring easing for the ready button reveal and theme-change bounce. Keep these deliberate exceptions to restrained motion. Other motion explains entrance, selection, saving, or removal. Reduced motion disables CSS animation/transitions and scripted flights/bounces, removes shine, and skips the glide.

**Keyboard:** Enter submits the name form; Escape resets account editing. Cmd/Ctrl+/ removes the selected account. Cmd/Ctrl+Enter opens the handoff only when ready and no account mutation is running. Key chips are hints, not extra focus targets. Icon controls have accessible names.

## Do's and Don'ts

- Do reuse the semantic CSS properties and both theme treatments.
- Do keep focus visible, keyboard hints accurate, and reduced motion complete.
- Do keep footer actions clear of the editor at narrow widths and short heights.

- Don't replace the supplied visual authority with a new palette or font.
- Don't reduce secondary or placeholder contrast to match the paler mockup.
- Don't treat deferred review components or mockup timers as implemented behavior.
