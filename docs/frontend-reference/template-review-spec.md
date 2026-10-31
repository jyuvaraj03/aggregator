# Template Review — screens, motion and design system

This document describes the transaction template review flow as built in the interactive mockup. It covers every screen and state, every animation with its timing, the keyboard model, and the design system the screens are built from. Values are taken directly from the mockup, so they can be used as the implementation reference.

**What the product does.** The app syncs a person's inbox and finds bank emails that share a layout. It groups them into *templates* and reads the values that matter out of each email: amount, currency, payee and date. The person checks each template once, picks the account it belongs to and corrects any tags. Every email in that template is then saved as a transaction the same way.

---

## 1. Flow at a glance

| # | Screen | Purpose | Leaves when |
|---|---|---|---|
| 1 | Syncing | Shows the inbox is being read | After 2 s, the line moves to the bottom |
| 2 | Add your accounts | Create the accounts transactions belong to | "See templates" is pressed (available from 10 s) |
| 3 | Templates found | Marks the hand-off into review | Automatically, after ~2 s |
| 4 | Review (one template at a time) | Confirm, edit or reject each template | All templates are decided |
| 5 | All templates reviewed | Summary | "Review again" |

Two bottom sheets can open over the review: **Accounts** (create, edit, remove accounts) and **Move transactions** (reassign transactions before an account is removed). Templates we are unsure about are always placed **last** in the queue.

---

## 2. Screens

### 2.1 Syncing

- A single line, **"Syncing emails…"**, centred on an empty page, in Heading 2 with a moving shine (see §4.1).
- After **2 s** it glides to the bottom centre of the screen, shrinking from 20 px to 17 px. The account setup screen then fades in behind it.
- It keeps shining at the bottom while accounts are added.
- **10 s** after the start, the bottom line turns into a primary **"See templates"** button with a light sweep across it, and a ⌘↵ hint.

### 2.2 Add your accounts

**Layout.** The content sits in a centred column 340 px wide:

- **Heading:** "Add your accounts" (Heading 1).
- **Helper line:** "Add each bank account, debit card and credit card on its own, so you can tell their transactions apart." (Body, muted, max 380 px wide, centred.)
- **Card preview:** full width at a 16:9 ratio.
- **Fields:** Account name and Theme side by side, with the Theme column 84 px wide.
- **Primary button:** "Add account" ↵.
- **Note:** "You can add more accounts later, too." (Small, muted.)

**Card preview.**
- **No name yet:** the preview is a silver, frosted card with "Account name" in placeholder grey, tinted faintly with the chosen theme.
- **Name typed:** it fades into the full coloured card with its pattern, and the name sits top-right on up to 2 lines.

**Account name.**
- The name is limited to **40 characters**.
- A counter ("30/40") appears from 30 characters and turns red at 40.

**Theme.** The swatch opens a 5 × 4 grid of the 20 theme colours (§5.6). Each colour carries its own pattern, so choosing a colour also chooses the pattern.

**The stack of accounts.**
- **Position:** created accounts are stacked on the left edge of the screen, partly off-canvas, overlapping vertically.
- **Spacing:** the gap is 28–92 px and shrinks to fit the screen height.
- **Add card:** the stack ends with a silver **"+ Add account"** card. It only appears once at least one account exists.
- **Hover:** a card rises 10 px.
- **Selected:** the card slides 24 px right, staying at hover height, and loads into the editor.

**Editing an existing account.**
- **Main button:** becomes "Save changes".
- **Remove:** a red "Remove account" button appears below it, with the ⌘ / hint.
- **Note:** reads "Editing {name}".
- **Text cursor:** goes to the end of the name; the text is never pre-selected.

**Rules.**
- **Names:** duplicate names are refused with a message.
- **Remove:** removing an account with tagged transactions opens the Move transactions sheet (§2.6).

### 2.3 New transaction email templates found

- **Ripple:** a blue ripple expands from the centre of the screen: a soft filled circle plus two thin rings.
- **Message:** "New transaction email templates found" (Heading 2, brand blue) rises in partway through the ripple.
- **Hand-off:** it holds for about 1 s, then the screen fades into Review.

### 2.4 Review

**Layout.** The layout is two columns under a centred header:

- **Header:** a progress line, "You've reviewed {n} of {total} templates so far" (Body, muted), above the question in Heading 1.
- **Left column (460 px):** the clipboard. A binder clip sits over a pile of email papers, with Previous / Next and a "Viewing n of m emails" pill below.
- **Right column (400 px):** the transaction card, then the controls.
- **Column gap:** 96 px.

**Scaling.** The whole layout is scaled once to fit the window when the screen opens, never more than 100 %. It is not rescaled later.

#### The clipboard and papers

- **Size:** every email sits on the same size of paper (540 px tall); long emails scroll inside it, vertically only. A fade at the bottom hints at more content.
- **Pile edges:** up to two paper edges peek 7 px below the top paper, one per email still to view. They disappear as you reach the last email.
- **Shadow:** only the top paper has a soft shadow; the others have a faint bottom hairline.
- **Viewed papers:** they stack to the left and are cut off by the clipboard edge, leaving a ~20 px strip. Their text fades to 28 %.
- **Highlights:** detected values are shown as coloured outlined boxes. Amount and currency are pink, payee blue, date yellow and description green.
  - Hovering a box shows a filled label above it in the matching colour, such as "Payee".
  - Currency and amount share a single "Transaction amount" label over the pair.
  - A label flips to the right edge if it would leave the paper.
- **Unassigned values:** detected values that aren't assigned to a field look like plain text in view mode. They appear as grey "Not assigned" boxes only in edit mode.

#### Transaction card

- **Payee:** the top line (Meta size).
- **Amount:** a muted sign, then the currency code in bold 17 px, then the amount in Display size.
  - **Sign:** **−** for debit or **+** for credit, at 24 px.
  - **Currency code:** always the ISO 4217 code (Rs., ₹ → INR). Several currency values are joined, and anything over 6 characters is shortened with "…".
  - **Amount:** formatted with Indian digit grouping (1,24,380.00).
- **Date and account row:** the date sits on the left and the account on the right, with a colour dot and its name, or "No account selected" when empty. If the date grows, the account drops to its own line.
- **Description (optional):** sits in a light grey strip across the bottom of the card, shown only when filled in.
- **Edge:** the card has a darker hairline and a soft shadow.

#### Controls: view mode

- **Account name:** a searchable dropdown (§5.8.2) with the placeholder "Select account".
- **"Looks right!":** primary button, ↵, 10 px under the account field. It is always enabled. If no account is chosen, the field jiggles, turns red and opens.
- **Bottom row**, aligned with the bottom of the clipboard:
  - **"Edit tags":** secondary button, ⌘↵, full width.
  - **Retry tagging with AI:** icon-only button with a refresh icon and the tooltip "Retry tagging with AI".
  - **Not a transaction:** icon-only pink button with a ✕ and the tooltip "Not a transaction".

#### Controls: unidentified template ("Is this a transaction email?")

- **Heading:** "Is this a transaction email?".
- **Email:** shows as plain text, with no highlights.
- **Card:** a static placeholder with grey bars and no shimmer.
- **Buttons:** only two — "This is a transaction email" (primary, ↵) and "This is not a transaction" (danger, full width).
- **On confirm:** the heading changes back, a scan sweeps the paper (§4.6), the values light up, the card fills in, and the normal controls rise in.

#### Controls: edit mode ("Edit tags")

**Scrolling.** The card stays fixed. Everything below it scrolls inside the column, which stays exactly as tall as the clipboard. Fields fade out under the card at the top, and the bottom button row stays pinned with a fade above it. Nothing scrolls sideways.

**Contents, top to bottom:**

1. **Account name:** the same dropdown as in view mode.
2. **Debit / Credit toggle:** a grey segmented control 64 px tall, with the selected side in white.
3. **Tag fields** (§5.8.3):
   - Date of transaction
   - Payee
   - Currency
   - Transaction amount
   - Description (optional)
   - Each field is on its own row, 22 px apart.
4. **"Done editing"** (primary, ↵), with an icon-only **Reset changes** button beside it. Reset puts every field and the toggle back to how they were when edit mode opened.

**Rules.**
- **Multiple values:** a field can hold several values, which are joined on the card.
- **Shared values:** the same value can sit in more than one field.
- **Fixed values:** any typed text can be added as a fixed value; it applies to every email in the template.
- **Missing fields:** on "Done editing", required fields with no values jiggle and turn red. Description is optional.
- **Scope:** edits apply to every email in the template, and paging between emails still works in edit mode.
- **Esc:** leaves edit mode without saving.

### 2.5 Accounts sheet ("Manage accounts" / "Add new account")

- **Opening:** it opens from the account dropdown, either through **Add new account “…”** (shown when the typed name doesn't match an account) or through **Manage accounts**, which is always the last item.
- **Layout:** a full-width bottom sheet, up to 600 px or 88 % of the window tall. It uses the same layout as the setup screen, with the account stack on the left and the editor centred. The title reads "New account" or "Edit account".
- **New account:** the name comes pre-filled from what was typed, and the next unused colour is chosen.
- **Edit account:** shows "Save changes" and a red "Remove account" button with no shortcut. A note under the buttons gives the number of tagged transactions.
- **Creating from the dropdown:** this selects the new account for the current template and closes the sheet. Creating from Manage keeps the sheet open.

### 2.6 Move transactions sheet

- **When it opens:** it replaces the Accounts sheet, or opens over the setup screen, when you remove an account that already has tagged transactions.
- **Animation:** small papers fly in an arc from a mini card in the removed account's colour into a second card. The second card is silver until a destination is chosen.
- **Title:** "Move transactions before removing".
- **Explanation:** "{n} transactions from {t} templates are tagged with {name}. Choose where they should go, then the account is removed."
- **"Move transactions to":** a dropdown of the other accounts, which can also create a new one. It doesn't open by itself.
- **Buttons:**
  - **"Move and remove" (↵):** reassigns the transactions, removes the account and returns to the Accounts sheet.
  - **"Cancel":** returns to the Accounts sheet with the same account selected.

### 2.7 All templates reviewed

- **Summary:** for example "4 confirmed, 1 edited and confirmed, 1 not transactions".
- **Title:** "All templates reviewed".
- **Button:** "Review again" ↵, which restarts the flow.

### 2.8 Always available

- **Theme toggle:** a 40 × 40 icon button (moon / sun) in the top-right corner. The choice is remembered, and dark mode swaps in the dark binder clip.
- **Messages (toasts):** a dark pill near the bottom centre, shown for 2.2 s.

---

## 3. Keyboard

| Context | Key | Action |
|---|---|---|
| Setup | ↵ | Add account / Save changes |
| Setup | ⌘↵ | See templates (once available) |
| Setup, editing an account | ⌘ / | Remove account |
| Setup, editing an account | Esc | Back to a new account |
| Review | ↵ | Looks right! |
| Review | ⌘↵ | Edit tags |
| Review | ← → | Previous / next email (when not typing) |
| Review | any letter | Focuses the account field and starts searching |
| Unidentified template | ↵ | This is a transaction email |
| Edit mode | ↵ or ⌘↵ | Done editing |
| Edit mode | Esc | Cancel edit mode |
| Any dropdown | ↓ ↑, ↵, Esc | Move, choose, close |
| Tag field | Backspace (empty input) | Remove the last tag |
| Sheets | ↵ / Esc | Main action / close |
| Done | ↵ | Review again |

Ctrl replaces ⌘ on Windows and Linux. Esc never rejects a template.

---

## 4. Motion

All motion respects **reduced motion**, where animations jump to their end state.

**Easing curves:**

| Name | Curve | Used for |
|---|---|---|
| Ease | `cubic-bezier(.2,.7,.2,1)` | Default for entrances |
| Ease-in | `cubic-bezier(.5,0,.75,0)` | Exits |
| Spring | `cubic-bezier(.34,1.45,.55,1)` | The clip and the See templates button |

**Rise:** most elements enter by fading in while moving up from 14 px below (520 ms, Ease).

### 4.1 Shine (Syncing text)

- **Effect:** a light band sweeps across the text, using a background-clipped gradient.
- **Timing:** loops every 2.2 s (ease-in-out); the sweep takes the first 60 % of each cycle.

### 4.2 Syncing → setup

| Step | Timing |
|---|---|
| Centre text fades in | 400 ms |
| Holds | 2 s |
| Glides to the bottom bar | 700 ms, `cubic-bezier(.6,0,.2,1)`, font 20 → 17 px |
| Setup heading rises | starts as the glide ends |
| Helper line rises | +60 ms |
| Card, fields, button and note rise | each +90 ms after the previous, starting at 120 ms |

**See templates (at 10 s):** the bottom line fades down (220 ms, Ease-in), then the button springs in (420 ms, scale .94 → 1). A white light sweeps across it every 2.6 s.

### 4.3 Accounts

- **Add:** the preview card flies onto the stack in 560 ms (`cubic-bezier(.3,.7,.2,1)`), scaling from preview size to stack size. A fresh preview then fades in (380 ms, 220 ms delay).
- **Hover / select in the stack:** CSS transitions, 300 ms. Selecting moves only the card; the stack is never rebuilt.
- **Remove:** the card slides out 80 px left while fading (260 ms, Ease-in).
- **Name typed or cleared:** the card cross-fades between silver and colour (380 ms).
- **Colour picked:** the card does a small bounce (260 ms, Spring).
- **Bottom sheets:** slide up in 420 ms (`cubic-bezier(.2,.8,.2,1)`) and down in 280–300 ms (Ease-in). The scrim fades over 200–220 ms.
  - **Hand-off:** when one sheet hands over to another, the scrim stays on.
- **Move papers:** each cycle takes 2.4 s and three papers loop, starting 0.8 s apart. Each paper rises 26 px at the midpoint of its arc and turns from −10° to 12°. It also grows from 0.8 to 1 scale and back, fading in and out at the ends.

### 4.4 Templates found

- **Ripple:**
  - The filled circle grows over 1300 ms.
  - The first ring grows over 1500 ms, starting 120 ms in.
  - The second ring grows over 1600 ms, starting 300 ms in.
  - All three expand to 1.15 × the screen diagonal on `cubic-bezier(.22,.61,.36,1)`.
- **Message:** rises at 450 ms (450 ms long).
- **Hand-off:** after about 1.55 s the screen fades out (320 ms).

### 4.5 Review entrance (first template)

| Element | Starts at | Animation |
|---|---|---|
| Progress line | 0 ms | Rise |
| Question | 80 ms | Rise |
| Clipboard panel | 220 ms | Rises from 24 px below (600 ms) |
| Binder clip | 560 ms | Drops from 36 px above (520 ms, Spring) |
| Papers | 760 ms | Rise from 56 px below with −1.5° tilt (620 ms) |
| Previous / next | 1000 ms | Rise |
| Transaction card | 1180 ms | Rise |
| Account field | 1300 ms | Rise |
| Looks right! | 1390 ms | Rise |
| Edit tags | 1470 ms | Rise |
| Retry tagging | 1510 ms | Rise |
| Not a transaction | 1550 ms | Rise |

### 4.6 Within a template

- **Next email:** the top paper slides straight left onto the viewed stack (560 ms, `cubic-bezier(.3,.7,.2,1)`), travelling above everything else.
  - **Pile:** the papers below move up a level (450 ms transition).
  - **Text:** the moving paper's text fades to 28 % (500 ms).
- **Previous email:** the reverse; the paper returns to the centre over the pile.
- **Card wipe:**
  - The old values are wiped away in the paper's direction (480 ms, 60 ms delay, `cubic-bezier(.65,0,.35,1)`), with a faint blue sheen along the edge.
  - The new payee, amount and date row then fade and slide in from 16 px, each starting 70 ms after the previous (380 ms).
- **Scan:**
  - **Beam:** a 120 px blue beam with a glowing edge sweeps down the paper in 1700 ms (`cubic-bezier(.45,.05,.55,.95)`). A faint tint fills in behind it.
  - **Values:** each one pops in (scale .92 → 1.06 → 1, 360 ms) as the beam passes it.
  - **End:** the overlay fades out in 260 ms.
- **Retry tagging with AI:** the icon spins once (800 ms), and the card resets to its placeholder while the scan runs.
- **Edit mode in/out:** the current controls fade down 8 px (160 ms, 25 ms stagger), then the new ones rise (420 ms, 70 ms stagger).
- **Debit/Credit switch:** the amount nudges in from 6 px left (260 ms).
- **Dropdown open:** the list fades in from 4 px above (150 ms).
- **Feedback:**
  - **Button press:** scales to 0.98 (180 ms).
  - **Shake for missing input:** the field moves ±6 px (320 ms).

### 4.7 Between templates

- **Out:**
  - The clip lifts 12 px (260 ms).
  - The card fades up (240 ms).
  - Previous / next fade out (200 ms).
  - The papers slide up 24 px and fade (340 ms, Ease-in).
- **In:**
  - New papers rise from 56 px with a 1.5° tilt (560 ms).
  - The clip settles back with a spring (420 ms, 320 ms delay).
  - Previous / next rise (260 ms delay).
  - The card rises (200 ms delay).
  - Controls rise from 260 ms, each 70 ms after the previous.
- The header stays in place.

### 4.8 Finish

All review elements fade up and out in 260 ms, each starting 30 ms after the previous. The summary, title and button then rise in at 0, 90 and 220 ms.

---

## 5. Design system

### 5.1 Principles

- **Paper on a calm desk.** The ground is a very light cool grey. Content sits on white paper and cards. Only the email you're reading carries a shadow.
- **One question per screen.** Each screen leads with a single question or instruction in Heading 1. Answers are phrased the way the person would say them ("Looks right!", "Edit tags").
- **Colour carries meaning.** Pink, blue, yellow and green mean amount, payee, date and description, both in the email and on the matching field. Grey means "detected but not assigned". Indigo means a fixed value. Brand blue is reserved for system moments: the ripple, the scan, focus rings and selected options. It is never a button fill.
- **Every action has a key.** Buttons show their shortcut in a chip.

### 5.2 Colour tokens

Light and dark values for every colour token.

**Surfaces**

| Token | Light | Dark |
|---|---|---|
| `--surface-page` | `#f4f6f9` | `#14171c` |
| `--surface-panel` | `#f9fafc` | `#1a1e24` |
| `--surface-paper` | `#ffffff` | `#22272e` |
| `--surface-paper-edge` | `#f3f4f7` | `#1e2329` |
| `--desc-strip` | `#f9fafb` | `#1e2329` |

**Borders**

| Token | Light | Dark |
|---|---|---|
| `--border-card` | `#dce0e7` | `#343b45` |
| `--border-input` | `#e1e5eb` | `#3a414b` |
| `--border-divider` | `#e7e9ed` | `#2f353e` |
| `--card-line` | `#d2d8e1` | `#3a414b` |

**Ink (text)**

| Token | Light | Dark |
|---|---|---|
| `--ink-strong` | `#1f242c` | `#f1f3f6` |
| `--ink-body` | `#333c49` | `#d3d8df` |
| `--ink-heading` | `#505b6c` | `#c6cdd7` |
| `--ink-meta` | `#7b8088` | `#9aa3b1` |
| `--ink-muted` | `#8a93a3` | `#8790a0` |
| `--ink-placeholder` | `#c5cbd3` | `#616a78` |

**Actions**

| Token | Light | Dark |
|---|---|---|
| `--action-primary` | `#393a3e` | `#e8ebf0` |
| `--action-primary-hover` | `#2c2d30` | `#ffffff` |
| `--action-primary-ink` | `#ffffff` | `#14171c` |
| `--action-secondary` | `#e3e7ed` | `#2a3038` |
| `--action-secondary-hover` | `#d8dde5` | `#353c46` |
| `--action-secondary-ink` | `#3a4352` | `#d3d8df` |
| `--action-danger` | `#f2dde3` | `#36222a` |
| `--action-danger-hover` | `#ecd0d9` | `#432830` |
| `--action-danger-ink` | `#c4162f` | `#ff8b9c` |

**Key chips**

| Token | Light | Dark |
|---|---|---|
| `--key-chip-primary` | `#4a4b50` | `#d0d5dc` |
| `--key-chip-primary-ink` | `#9a9ba0` | `#4a5260` |
| `--key-chip-secondary` | `#d3d8e0` | `#3a414b` |
| `--key-chip-danger` | `#e6d1d8` | `#4b2c35` |
| `--key-chip-ink` | `#5b6473` | `#aab2bf` |

**Navigation & controls**

| Token | Light | Dark |
|---|---|---|
| `--nav-surface` | `#d7dde6` | `#2a3038` |
| `--nav-ink` | `#62779a` | `#a4b6d4` |
| `--nav-pill` | `#e9edf2` | `#232830` |
| `--nav-pill-ink` | `#4d5f7e` | `#b9c6dc` |
| `--label-grey` | `#e6e9ee` | `#2a3038` |
| `--seg-on` | `#ffffff` | `#3c434e` |
| `--brand-blue` | `#3b71c6` | `#79a3e6` |

**Highlights: amount & currency**

| Token | Light | Dark |
|---|---|---|
| `--var-amount-bg` | `#fdf0fb` | `#3a2236` |
| `--var-amount-line` | `#eea3e0` | `#a8569b` |
| `--var-amount-ink` | `#ad3596` | `#f0a6e2` |

**Highlights: payee**

| Token | Light | Dark |
|---|---|---|
| `--var-merchant-bg` | `#eaf4fb` | `#1b3040` |
| `--var-merchant-line` | `#8cc1e4` | `#4a87b1` |
| `--var-merchant-ink` | `#23699a` | `#8dc6ee` |

**Highlights: date**

| Token | Light | Dark |
|---|---|---|
| `--var-date-bg` | `#fefbdf` | `#322f19` |
| `--var-date-line` | `#d4c947` | `#a1972f` |
| `--var-date-ink` | `#786d0a` | `#e2d777` |

**Highlights: description**

| Token | Light | Dark |
|---|---|---|
| `--var-desc-bg` | `#eef7f2` | `#18332a` |
| `--var-desc-line` | `#93cfb2` | `#4a9a78` |
| `--var-desc-ink` | `#2d7656` | `#8fd8b6` |

**Highlights: not assigned**

| Token | Light | Dark |
|---|---|---|
| `--var-other-bg` | `#f3f4f6` | `#2a2f37` |
| `--var-other-line` | `#b4bbc6` | `#5a6270` |

**Fixed-value tags**

| Token | Light | Dark |
|---|---|---|
| `--fixed-bg` | `#eef0fb` | `#262b4a` |
| `--fixed-line` | `#aab2e6` | `#5e68b8` |
| `--fixed-ink` | `#3c4796` | `#b7befa` |

**Selected option**

| Token | Light | Dark |
|---|---|---|
| `--sel-bg` | `#eef4fd` | `#1d2a3d` |
| `--sel-bg-active` | `#e3edfc` | `#233349` |
| `--sel-chip` | `#ffffff` | `#22272e` |
| `--sel-line` | `#8eb1e6` | `#4c76b5` |
| `--sel-ink` | `#2f62b3` | `#8fb4ee` |
**Highlight hover-label fills:**

| Value | Label fill |
|---|---|
| Amount / currency | `#d382d1` |
| Payee | `#4a93c8` |
| Date | `#a0951a` |
| Description | `#4f9e7a` |
| Not assigned | `#959dab` |

Label text is always white.

**Missing-field state:**

| Part | Light | Dark |
|---|---|---|
| Line | `#e59aa7` | `#e59aa7` |
| Tab fill | `--action-danger` | `--action-danger` |
| Tab text | `--action-danger-ink` | `--action-danger-ink` |
| Glow | `--action-danger-ink` at 10 % | `--action-danger-ink` at 10 % |

### 5.3 Typography

**Typeface:** Schibsted Grotesk (variable, 400–900), bundled locally. Fallbacks: `ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif`. Use the font's proportional figures; don't turn on tabular numerals.

| Token | Size / line height | Weight | Used for |
|---|---|---|---|
| `--fs-display` | 34 / 40 | 700 | The amount on the transaction card |
| `--fs-h1` | 28 / 36 | 600 | Screen headings ("Does this transaction look right?", "Add your accounts") |
| `--fs-h2` | 20 / 28 | 600 | Sheet titles, "Syncing emails…", "Templates found" |
| `--fs-control` | 17 / 24 | 500 inputs · 600 buttons | All buttons and inputs, and the syncing line at the bottom |
| (control-s) | 16 / 22 | 600 / 400 | Debit/Credit toggle (600), "Viewing n of m emails" (400) |
| `--fs-body` | 15 / 22 (email body 15 / 26) | 400 | Email text, dropdown options, tags, messages, progress line, card date row, helper text |
| `--fs-meta` | 14 / 20 | 400 | Sender, payee line and description on the card |
| `--fs-small` | 13 / 18 | 500 labels · 400 text | Field labels, received time, data types, tooltips, hover labels (600), key chips |
| `--fs-caption` | 12 / 16 | 500 | Character counter, "Fixed" badge, "(optional)" |

**Other text sizes:**
- **Account card name:** 18 / 24, weight 500.
- **Currency code on the card:** 17 px bold.
- **Sign on the card:** 24 px, weight 400, muted colour.

### 5.4 Spacing and layout

**Spacing steps** (`--space-*`): 4, 8, 12, 16, 24, 32, 48 px.

| Element | Measurement |
|---|---|
| Review columns | 460 px + 400 px, 96 px gap |
| Paper | 540 px tall, 380 px wide |
| Clipboard panel | 40 px side padding, 40 px bottom padding |
| Header to content | 84 px |
| Fields in edit mode | 22 px apart |
| Account field to Looks right! | 10 px |
| Card to fields in edit mode | 8 px, plus a 26 px fade |
| Buttons and fields | 64 px tall in review; 52 px in the setup editor and sheets |
| Icon buttons | 64 × 64 px |
| Theme toggle | 40 × 40 px |
| Account cards | 320 × 180 px in stacks; preview at 16:9 |

### 5.5 Radius and elevation

**Radius:**

| Token | Value | Used for |
|---|---|---|
| `--radius-xs` | 6 px | Chips and highlights (7 px in the email) |
| `--radius-md` | 12 px | Papers and the previous / next buttons |
| `--radius-lg` | 16 px | Buttons, fields and the transaction card |
| `--radius-xl` | 24 px | The clipboard panel |
| `--radius-pill` | 999 px | Count pill and toasts |

Field label tabs use 8 px corners on top only. Bottom sheets use 28 px corners on top.

**Shadows:**

| Element | Shadow |
|---|---|
| Top paper (light) | `0 2px 4px rgba(31,36,44,.05), 0 10px 24px rgba(31,36,44,.07)` |
| Other papers | `0 1px 1px rgba(31,36,44,.07)` |
| Transaction card | `0 1px 2px rgba(31,36,44,.04), 0 6px 18px rgba(31,36,44,.06)` |
| Menus | `0 14px 36px rgba(31,36,44,.14)` |
| Sheets | `0 -12px 40px rgba(31,36,44,.16)` |
| Dark mode | Darker black-based equivalents of each |

### 5.6 Account cards

- **Colours:** 20 theme colours.

  | Name | Hex | Name | Hex | Name | Hex | Name | Hex |
  |---|---|---|---|---|---|---|---|
  | Ocean | `#1f6f94` | Cobalt | `#2856b8` | Indigo | `#3f3d9e` | Violet | `#6a3fa8` |
  | Plum | `#7d3b78` | Orchid | `#b04fa6` | Rose | `#c23f6e` | Crimson | `#b3202f` |
  | Brick | `#a8442a` | Saffron | `#d97a1c` | Turmeric | `#c79a12` | Olive | `#6f7a24` |
  | Leaf | `#3f8a3a` | Emerald | `#1e8064` | Teal | `#18837f` | Peacock | `#0d6e8c` |
  | Slate | `#4d5b70` | Graphite | `#34383f` | Cocoa | `#6b4a3a` | Sand | `#9c8463` |

- **Fill:** a 135° gradient from the colour mixed 18 % with white, through the colour itself, to the colour mixed 38 % with black.
- **Name:** in the colour mixed 80 % with white.
- **Patterns:** eight patterns in white or black at 5–22 % opacity: fold, rings, waves, dots, bands, arcs, chevrons and tiles. Colour *n* uses pattern *n* mod 8.
- **Silver card** (Add account, and any card without a name yet): a frosted white gradient with a 10 px backdrop blur, a white inner edge and a diagonal sheen. An unnamed card adds a faint wash of its chosen colour.

### 5.7 Buttons

| Variant | Fill / text | Used for |
|---|---|---|
| Primary | `--action-primary` / `--action-primary-ink` | Looks right!, Done editing, Add account, Create / Save, Move and remove, See templates |
| Secondary | `--action-secondary` / `--action-secondary-ink` | Edit tags, Cancel, Review again |
| Danger | `--action-danger` / `--action-danger-ink` | This is not a transaction, Remove account |
| Icon | 64 × 64, secondary fill (or danger for ✕) | Retry tagging, Not a transaction, Reset changes |

- **Shape:** 64 px tall, 16 px radius.
- **Label:** left-aligned, 17 / 600.
- **Key chips:** on the right, 30 × 30 with 6 px radius; on primary buttons they are a darker shade of the button.
- **Tooltips on icon buttons:** a grey pill (`#6f7887`, white 13 px text) below the button. In the bottom row of edit mode it appears above instead, aligned to the button's right edge.

### 5.8 Fields

#### 5.8.1 Labelled field (shared)

- **Label:** a small tab above the field, 13 / 500, joined to the field's 2 px border. The field and tab share the colour set for their role.
- **Field:** 64 px tall, 16 px radius, white fill, text 17 / 500.
- **Account and Theme:** use a grey tab (`--label-grey`) with `--ink-heading` text.
- **Description:** stays grey until it has a value, then turns green.

#### 5.8.2 Searchable dropdown (single choice: accounts)

- **Opening:** clicking anywhere in the field opens the list. While you search, the current value moves into the placeholder, and typing filters the list.
- **Options:** each shows a colour swatch and the account name. The current account is highlighted in light blue (`--sel-bg`).
- **Extra items:**
  - **"+ Add new account “…”:** appears when nothing matches what you typed.
  - **"Manage accounts":** always last, below a divider.
- **Placement:** the list opens upward when there isn't room below.

#### 5.8.3 Tag field (multi-value: transaction fields)

- **Values:** shown as tags. Grey tags are detected values; indigo tags are fixed values. Each tag has a × to remove it.
- **Typing:** the text cursor sits right after the last tag. Long tags are shortened with "…". The field grows to fit additional lines of tags.
- **Placeholder:** "Search for a field", or "Add if this template has one" for Description.
- **List:** every value detected in the email, as a grey chip with its data type on the right (Number, Text, Date & time or Currency code).
  - **Selected options:** blue, with a ✓.
  - **Fixed value:** while typing, the list ends with "+ Add “…” as a fixed value".

#### 5.8.4 Debit / Credit toggle

- **Track:** 64 px tall, `--action-secondary` fill, 12 px radius, 4 px padding.
- **Options:** labels are 16 / 600. The selected option has a `--seg-on` fill with a 1 px shadow.

### 5.9 Copy

**Tone:** sentence case and plain verbs throughout. Messages confirm what happened: "Saved 5 transactions to DCB Niyo", "Template updated for all 4 emails", "Retried tagging with AI", "Changes reset", "Removed {name}".

**Key strings:**

| Where | String |
|---|---|
| Review heading | Does this transaction look right? |
| Unidentified heading | Is this a transaction email? |
| Setup heading | Add your accounts |
| Setup helper | Add each bank account, debit card and credit card on its own, so you can tell their transactions apart. |
| Setup note | You can add more accounts later, too. |
| Card, empty account | No account selected |
| Card, empty fields | Payee not set / Date not set / — |
| Empty account field | Select account |
| Empty tag field | Search for a field |
| Empty description field | Add if this template has one |

### 5.10 Accessibility

- **Contrast:** text meets 4.5:1 on its surface in both themes. Muted text is reserved for secondary information.
- **Focus:** every control has a visible 2 px brand-blue focus ring.
- **Not colour alone:** fields always carry a text label, and highlights carry a text label on hover and focus.
- **Screen readers:** icon-only buttons have accessible names. The transaction card is announced politely when it changes.
- **Reduced motion:** turns off the shine, ripple, flights and scan animation.

---

## 6. Data model (for implementation)

```
Template
  subject        string (may contain {c}{a})
  from           sender address
  body           string[] — paragraphs with {x} placeholders for detected values
  map            { date, merchant, currency, amount: tokenKey }   // the AI's first guess
  desc?          [{ fixed: "…" }]                                  // optional default description
  type?          "debit" | "credit"   (default "debit")
  unknown?       true when we are not sure it is a transaction template
  emails         [{ [tokenKey]: string, t: ISO datetime received }]

Field mapping while reviewing
  { date | merchant | currency | amount | description: Item[] }
  Item = { k: tokenKey }  (a detected value)  |  { fixed: string }  (same for every email)

Account
  { id, name (≤ 40 chars), color (0–19) }
```

Money values are split when the template is loaded. "INR 1311.0" becomes a currency token ("INR") and a number token ("1311.0"), so the two can be tagged separately.
