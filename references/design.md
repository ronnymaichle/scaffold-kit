# Design system, feedback and UI text

Becomes `docs/DESIGN.md`. Keep what applies to the stack and profile; replace the scaffold-time sections with the decisions (source colors and rationale, the look, styling approach, component base, toast library) and their reasons.

## Colors: always ask (scaffold-time)

Never invent a palette silently. Offer three paths and wait for the answer:

1. The user gives colors (hex, names or a logo): derive the full theme from them.
2. The user describes a mood or references: propose 2-3 themes.
3. The user asks for a recommendation: propose 2-3 themes suited to the app's domain and audience, each with a one-line rationale.

Colors are chosen at the plan step, with the draft (`docs/ARCHITECTURE.md`). Generate each proposal with the kit's palette script into the draft folder outside the project (proposals are for choosing, not for committing), and compare them on one page:

```bash
DRAFT="${TMPDIR:-/tmp}/plan-preview"
python3 "$KIT/scripts/quality/palette.py" theme --primary "#2563eb" --out "$DRAFT/themes/a.css"
python3 "$KIT/scripts/quality/palette.py" theme --primary "#0f766e" --highlight "#f59e0b" --out "$DRAFT/themes/b.css"
python3 "$KIT/scripts/quality/palette.py" preview "$DRAFT/themes/a.css" "$DRAFT/themes/b.css" --out "$DRAFT/themes/index.html"
```

The palette preview shows each proposal in light and dark: swatches, buttons, inputs, a card, alerts, toasts and the contrast results. The draft page links to it, and its screen mockups switch between the proposals. Never apply a theme the user has not approved; the approved CSS becomes the theme file listed in `quality.config.json` (`design.themeFiles`).

The script keeps a requested color exact wherever it passes contrast. When it cannot carry text in a role (for example a button background behind white text), the script derives the nearest accessible shade for that role and prints a note: keep the original as the `--highlight` color or an accent, and explain the change to the user.

## Look (scaffold-time)

Colors are only part of the look. Decide the rest with them, from the mood or references the user gave, so every screen looks like the same product instead of the component library's defaults. Recommend one option per item with a one-line reason, show it in the draft's screen mockups, and record the decisions and their reasons in a Look section of this file:

- Font: one interface font (for example Inter or Geist), a serif for reading-heavy apps (for example Source Serif), or the system stack for the lightest pages.
- Density: comfortable, the default for consumer apps, or compact for data-heavy tools; control heights and spacing steps follow it, and touch targets keep their minimums.
- Corners: the `--radius` token. About 0.25rem looks sharp and technical, 0.5-0.75rem soft (the generated theme uses 0.625rem), 1rem or more friendly and rounded.
- Motion: subtle (short fades and slides, the default) or minimal (state changes only), within the timing rule below.

The decisions become tokens and defaults: `--radius` in the theme file, the font family in the styling framework's theme (Tailwind v4: `--font-sans` in `@theme`), and the density as the default size of the base components.

## Screen mockups

For apps with screens, the draft includes rough mockups of the two or three screens users spend the most time in, starting with the main task, so the user sees the product before any code exists (scaffold-time):

- Plain HTML and CSS inside the draft page (`templates/plan-preview.html`), styled only with the theme's tokens, so the page's switches show every color proposal in light and dark. Layout uses container queries, so the page's width switch shows the phone and desktop layouts.
- Real labels and realistic fake data; each screen's main state, plus the empty state of the screen a new user lands on.
- They follow the UI and UX rules below and the component base's look, so the built screens can match them. Rough means no logic and no pixel polish, not grey boxes.

After approval, `docs/mockups/` keeps the screens: the draft page with only its screens and the approved theme left, and that theme's CSS file next to it. When a screen is planned, the `designer` starts from its mockup. The feature that builds a screen deletes its mockup in the same PR, and the folder goes with the last one, because a mockup that no longer matches the app misleads more than it helps.

## Palette derivation

What the script does; follow the same rules when adjusting by hand.

- Work in OKLCH. Each brand color gets an 11-step scale (50-950) that keeps its hue, steps lightness from ~0.97 to ~0.28 and tapers chroma at the extremes.
- Neutrals are grays lightly tinted toward the primary hue (chroma at most ~0.02).
- Semantic colors: destructive (red), success (green), warning (amber), info (blue), each a full scale.
- Roughly 60-30-10: neutrals dominate, the primary marks key actions, accents are sparse.
- Dark mode is designed, not inverted: tinted near-black surfaces (never pure #000), elevation shown by lighter surfaces (background, then card, then popover) instead of shadows, the primary shifted to a lighter, slightly less saturated shade, no pure white text on large areas, subtler borders.
- Meaning is never conveyed by color alone; pair it with an icon, text or shape.

## Tokens

- Names follow shadcn, so copied-in components work unchanged: `background`, `foreground`, `card`, `card-foreground`, `popover`, `popover-foreground`, `primary`, `primary-foreground`, `secondary`, `secondary-foreground`, `muted`, `muted-foreground`, `accent`, `accent-foreground`, `destructive`, `border`, `input`, `ring`. Added roles: `success`, `warning` and `info`. The four status roles (`destructive`, `success`, `warning`, `info`) each have `-foreground` (text on the solid color), `-subtle` (tinted background for alerts and banners) and `-text` (the role's color as readable text). Optional `highlight` and `highlight-foreground` for a second brand color; `overlay` for modal backdrops; `radius`.
- Defined once as CSS custom properties: the light theme on `:root`, the dark theme under `.dark` on `<html>`. Tailwind v4 maps them in `@theme inline` (`--color-background: var(--background)`), so components use semantic utilities (`bg-background`, `text-muted-foreground`, `bg-primary`, `border-input`, `bg-overlay`); Tailwind v3 maps them in the config's `theme.extend.colors`; without Tailwind, components use `var(--token)`.
- The `--palette-*` scales are inputs for the tokens, never used by components. Changing the theme means regenerating or editing one file.
- Spacing, radius, shadow, font, z-index and motion are tokens too (Tailwind's scale or custom properties).
- Tokens a component adds (for example shadcn's `sidebar-*` or `chart-*`) go into the theme file, derived from the palette scales, and their text and UI pairs go into `design.contrastPairs` in `quality.config.json`.

## Enforcement (part of `check`)

- `python3 scripts/quality/design_tokens.py literals` fails on color literals (hex, `rgb()`, `hsl()`, `oklch()`, named colors in color properties) and raw Tailwind palette classes outside the theme files. Replace them with tokens: `text-white` on a solid fill becomes that role's `-foreground` (`text-primary-foreground`, `text-destructive-foreground`); `bg-black/50` behind a dialog becomes `bg-overlay`; `text-red-600` becomes `text-destructive-text`. Copied-in components sometimes contain such literals; fix them when adding the component.
- A justified exception (a brand logo's fixed colors, a color a third-party embed requires) carries `design-check-ignore` and the reason on the same line, or its file goes into `design.allowLiteralsIn`.
- `python3 scripts/quality/design_tokens.py contrast` checks every foreground and background pair in both themes against WCAG 2 AA: 4.5:1 for text, 3:1 for component boundaries (`input` against its surface) and focus rings (`ring`). WCAG allows 3:1 for large text, but tokens are used at every size, so every text pair needs 4.5:1. Required pairs must exist; optional pairs are checked when both tokens exist. Its output fills the contrast table in this file.
- Input borders use `input`, which must reach 3:1 against the surface so fields stay visible (a light-gray decorative border does not); `border` is for dividers and may be lighter.

## Theme switching

- Three options: light, dark and system (the default, following `prefers-color-scheme`), stored in a cookie (a necessary preference cookie).
- Applied before first paint on every page: a tiny inline script in `<head>` reads the cookie, falls back to `prefers-color-scheme` for system, sets the `dark` class on `<html>` and follows OS changes while on system; the CSP allows it by its hash. When the cookie says light or dark, the server hook also renders the class into the HTML, so the page is right without JavaScript.
- `color-scheme` follows the theme, so native controls and scrollbars match.
- Third-party visuals (maps, charts, code blocks, embeds) get matching light and dark configurations.

## Styling choice by stack (scaffold-time)

Verify current versions and maintenance with a web search.

| Stack | Styling | Accessible component base | Feedback (toasts) |
|---|---|---|---|
| SvelteKit | Tailwind CSS (via `sv add`) with the token theme; Svelte scoped styles for component-specific layout | shadcn-svelte (Bits UI) | svelte-sonner (shadcn-svelte's Sonner) |
| React or Next.js | Tailwind CSS | shadcn/ui | Sonner (shadcn/ui's Sonner) |
| Vue or Nuxt | Tailwind CSS | shadcn-vue (Reka UI) or Nuxt UI | vue-sonner or Nuxt UI toasts |
| Solid | Tailwind CSS | Kobalte | Kobalte Toast |
| Server-rendered templates (Django, Rails, Go, HTMX) | Tailwind standalone CLI or plain CSS custom properties | Native HTML elements | Server-rendered flash messages |

Default to Tailwind when the user knows it; plain CSS with custom properties if they prefer it or the project is very small. Copied-in component libraries become owned code, restyled through tokens only. One icon set across the app (for example Lucide).

## Component composition

The UI is built from small parts in three levels, each using only the levels below it:

1. Base components from the component base (button, input, dialog): owned code, restyled through tokens only (for example `$lib/components/ui` with shadcn-svelte).
2. App components that combine them into the app's own concepts (a marker card, a comment list), in the shared components folder.
3. Screens: routes that put app components together with their data. Markup that repeats across screens becomes an app component on its third use (`docs/ARCHITECTURE.md`).

- The module-boundary lint rule enforces the levels (`docs/ARCHITECTURE.md`): base components never import app components, and components never import routes.
- Content goes in, not flags: when a component must show different content, the caller passes it in (Svelte snippets, React children, Vue slots). Style-only variants (size, tone) go through one variant helper (tailwind-variants with shadcn-svelte, cva with shadcn/ui). A component that needs more than about three boolean props to control its layout should be split, or take content instead.
- Shared behaviour (pagination, search, form state, a media query) lives in one function or reactive module (Svelte `.svelte.ts` modules with runes, React hooks, Vue composables), never copied between components.

## UI and UX rules

- Spacing on a 4px base scale, no arbitrary values; consistent radius and elevation tokens.
- Typography: one variable font, self-hosted (a font CDN would receive every visitor's IP address), or the system stack; a fixed type scale; body text at least 16px with ~1.5 line height; line length 60-75 characters.
- Mobile-first layouts; touch targets at least 44x44px for primary controls and never below 24x24px.
- Buttons: one primary action per view, then secondary, ghost and destructive; verb labels; every state designed: hover, active, a visible `focus-visible` ring, disabled, and loading (spinner, disabled, width preserved).
- Forms: visible labels (placeholders are not labels), correct input types and autocomplete, inline errors linked with `aria-describedby`, errors stated in text, server validation errors mapped back to their fields.
- Every data view handles loading (skeletons), empty (an explanation plus an action), error (message, retry, error ref) and success; every user action gets feedback through the global feedback system.
- Accessibility (WCAG 2.2 AA): semantic HTML first, full keyboard support, focus managed in dialogs and on route changes, alt text, landmarks, ARIA only where HTML is not enough, motion of 150-250ms reduced under `prefers-reduced-motion`.
- The dev design page: a dev-only route (404 in production) showing every token, the palette, the contrast results and every shared component and feedback state in both themes, updated whenever they change.
- axe-core checks run in the e2e suite on key pages and the dev design page, in both themes (`docs/TESTING.md`).

## Global feedback system

Installed once at the root and used everywhere:

- The toaster and the banner slot are mounted once in the root layout (SvelteKit: `src/routes/+layout.svelte`; React: the root layout or `App`).
- One `notify` module (for example `$lib/feedback`) is the only API features use: `notify.success()`, `notify.info()`, `notify.warning()`, `notify.error()`, `notify.promise()` (loading, then success or error) and `notify.fromError(error)`. Components never import the toast library directly, so it can be swapped.
- Server outcomes survive redirects: form actions and server redirects set a one-time flash message (cookie) that the root layout turns into a toast after navigation, and that renders as an inline banner when JavaScript is off.
- `notify.fromError` maps catalogued errors to their user-safe message and adds "Error ref: <requestId>"; the global client error handler uses it for unexpected failures (`docs/LOGGING.md`).

Pick the pattern by situation:

| Situation | Pattern | Behaviour |
|---|---|---|
| Result of a user action (saved, sent, copied) | Toast | Auto-dismisses after ~5s, pauses on hover and focus, has a close button |
| Reversible destructive action (delete, archive) | Toast with "Undo" | Happens immediately (soft delete); Undo restores it for ~10s; preferred over a confirmation dialog |
| Irreversible or high-impact action (delete account, publish to everyone) | Confirmation dialog | Names the consequence; the button says what it does ("Delete account") |
| Failed action | Error toast | Stays until dismissed; user-safe message, Retry when it makes sense, error ref |
| Form validation | Inline, next to each field | Never only a toast; focus moves to the first invalid field; a summary at the top of long forms |
| App-wide or persistent state (offline, maintenance, unverified email) | Banner at the top of the layout | Stays until the condition ends or the user dismisses it; one at a time, highest severity first |
| Long-running work (upload, video processing) | Progress on the item, toast on completion | Never blocks the page |

Rules:

- Variants use the status tokens (success, info, warning, destructive) in both themes, each with an icon and text, so color is never the only signal.
- Messages are short outcomes ("Marker saved", "Comment deleted"), translated when i18n is on, rendered as plain text (never HTML), and contain no personal data beyond what the user just entered.
- Accessibility: success and info toasts announce politely (`role="status"`), errors assertively (`role="alert"`); toasts never steal focus, are keyboard-dismissible and respect `prefers-reduced-motion`.
- Placement: bottom-right on desktop, bottom-center on mobile above any bottom navigation; at most 3 visible, newest first, duplicates collapsed.
- Tests: unit tests for `notify.fromError`; e2e tests assert the message, role and ref on key success and failure paths.

## UI text and languages

- Wording: plain and short; one term per concept across the UI, docs and errors; buttons say what they do; errors say what happened and what to do next, without blaming the user.
- One language with no plans for more: no i18n library (YAGNI), but user-facing text stays out of business logic (the error catalog holds the messages).
- Two or more languages, or more planned within a year: i18n is set up in Phase 1 (SvelteKit: Paraglide via `sv add`; React or Next.js: next-intl or i18next; Vue: vue-i18n; Python: Babel or gettext; Go: go-i18n; verify current options). All user-facing strings go through message files; the error catalog holds message keys, not text; dates, numbers and currencies are formatted with `Intl` (or the language's equivalent); emails, metadata, feedback messages and the consent banner are translated; layouts tolerate ~30% longer text; a lint rule or review step catches hard-coded user-facing strings.
- Language URLs and `hreflang`: `docs/SEO.md`.

## Lean profile

One generated theme (from the user's color or one recommendation) and one preview round; light and dark both come from the script. The look gets one recommendation, and the draft mocks up the main screen only. The token, literal and contrast checks stay. The dev design page and i18n are skipped unless needed.

## Strict profile additions

- A manual keyboard and screen-reader pass on the key flows before launch and after major UI changes, because automated checks find only part of the problems.
- An accessibility statement where the law requires one; check whether the European Accessibility Act applies (for example consumer e-commerce and banking services).
