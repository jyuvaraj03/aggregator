---
name: Aggregator
description: Established visual system for the email and template workflow.
colors:
  accent: "#245d48"
  accent-hover: "#194734"
  background: "#f6f7f4"
  surface: "#fff"
  text: "#202b27"
  muted: "#59645e"
  line: "#d9dfd8"
  secondary-text: "#273e32"
  control-hover: "#edf2eb"
  row-hover: "#edf1e9"
  input-border: "#a8b4aa"
  placeholder: "#626c65"
  focus: "#367b64"
  error: "#922d28"
typography:
  headline:
    fontFamily: '"Public Sans Variable", sans-serif'
    fontSize: "clamp(28px, 4vw, 38px)"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.03em"
  title:
    fontFamily: '"Public Sans Variable", sans-serif'
    fontSize: "19px"
    fontWeight: 650
    letterSpacing: "-0.02em"
  body:
    fontFamily: '"Public Sans Variable", sans-serif'
    lineHeight: 1.6
  label:
    fontSize: "13px"
    fontWeight: 600
rounded:
  input: "5px"
  control: "6px"
  panel: "12px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "11px 20px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.secondary-text}"
    rounded: "{rounded.control}"
    padding: "11px 20px"
  button-secondary-hover:
    backgroundColor: "{colors.control-hover}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.input}"
    padding: "10px 12px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "26px 28px"
---

# Design System: Aggregator

## Overview

This records the existing interface in `frontend/src/app/styles.css` and the
email and template components. The accepted direction preserves its typography,
colors, layout, and interaction patterns. It documents implementation facts;
it does not establish a new visual identity.

## Colors

The green accent marks primary actions, links, active navigation, and successful
results. Dark text and muted secondary text sit on an off-white page. White
panels use the line color for borders. Controls and rows have distinct pale
hover backgrounds. Errors use the error color and explicit text.

## Typography

Public Sans Variable is the interface family, with a sans-serif fallback.
Headlines and section titles use the frontmatter roles. Navigation uses 14px,
600-weight text; row subjects use 16px, 600-weight text. Sender, time, and paging
metadata use 13px. Counts and times use tabular numerals. Email bodies use 15px
text, a 1.8 line height, and a maximum width of 75ch. Template patterns retain
the browser's monospace `pre` family at 14px with a 1.8 line height.

## Layout

The header and main content share a centered 1120px maximum width. Main padding
is 48px 36px 64px. Lists are full-width rows separated by horizontal rules;
desktop rows place text, counts or dates, and a chevron in one line.

At widths up to 640px, main padding becomes 32px 20px 48px, the header can wrap,
forms and extraction controls stack, and row metadata moves below the text.
The body has a 320px minimum width. Template details stack the pattern, example
email, and matching-email list vertically. Patterns and email bodies preserve
line breaks and wrap long text. Template list previews stop after two lines.

## Elevation & Depth

The current interface has no box shadows. White surfaces, one-pixel borders,
dividers, and hover backgrounds distinguish content and interaction states.

## Shapes

Inputs, controls, and panels use the frontmatter corner radii. List rows have
square edges. Buttons, inputs, and navigation links have a minimum height of
44px. Email detail panels use responsive padding of `clamp(20px, 4vw, 40px)`;
pattern panels use `clamp(20px, 4vw, 32px)`.

## Components

- **Actions:** Primary buttons are green; pagination and retry buttons use the
  white secondary treatment. Disabled buttons have 0.5 opacity and a disabled
  cursor. Button backgrounds change on hover without a transition.
- **Inputs:** Visible labels sit above white fields with a one-pixel border.
- **Navigation:** Emails and Templates share the header. The active link has a
  pale background, green text, and an underline. Back links retain list paging.
- **Rows:** The full row is a link. Email sender and subject truncate with an
  ellipsis; template previews wrap. Counts and a chevron sit beside the copy.
- **Panels:** Sync and extraction controls use bordered white panels. Email
  details and examples separate metadata from plain-text bodies with a rule.
- **States:** Loading and success messages use status announcements; errors use
  alerts and retry controls. Empty lists use a bordered, centered text region.
  Extraction disables its action while pending and reports completion counts.
- **Focus and motion:** Focus-visible uses a three-pixel focus-colored outline
  with a four-pixel offset. A skip link appears on focus. Success messages reveal
  over 0.3 seconds with `ease-out`; reduced-motion preference disables this.

## Do's and Don'ts

- **Do** reuse the established typography, palette, panel treatments, row lists,
  responsive stacking, and keyboard focus behavior.
- **Don't** replace the incumbent visual system as part of extending the
  current email and template workflow.
