# FOCUS section + LAB topic tags

## Purpose

Fill in the "FOCUS" section deferred in `landing-plan.md` (§5) with Artem's
actual areas of interest, and introduce a lightweight topic-tag scheme for
LAB posts so future posts are categorized from day one.

## Topics

Three topics, each a short label + one-line gloss, in this order:

- **Data Viz** — BI dashboards, browser graphics, render-engine performance.
- **Full-Stack Architecture** — trends, architectures, best practices and
  patterns across the modern web stack.
- **AI Agents & Engineering** — trends, architectures and patterns for
  building and running agents in production.

Short mono tag forms (for the LAB tag scheme): `DATA VIZ`, `FULL-STACK`,
`AI AGENTS`.

## FOCUS section (homepage)

- New `<section id="focus">` in `index.html`, placed between `#hero` and
  `#lab` — reads as "who I am → what I'm focused on → what I've written."
- Structure mirrors `#lab`: a `.section-label` heading ("FOCUS") followed by
  a flat list of topic blocks (label + gloss), no cards/borders, consistent
  with the site's flat-text-block aesthetic (`landing-plan.md` §1).
- Markup shape per topic:
  ```html
  <li>
    <span class="topic-name">Data Viz</span>
    <span class="topic-gloss">BI dashboards, browser graphics, render-engine performance.</span>
  </li>
  ```
- New CSS: reuses `.section-label` as-is; adds `.topic-name` /
  `.topic-gloss` rules modeled on the existing `.feed .title` /
  `.feed .excerpt` rules (same type scale, spacing, uppercase/lowercase
  split). No new color, no accent — stays monochrome per the design tokens.
- Not a link, not interactive — plain text. No filtering wired to LAB.

## LAB topic tags

- Each LAB post gets one tag from the fixed set: `DATA VIZ`, `FULL-STACK`,
  `AI AGENTS`.
- Displayed next to the date, reusing the existing `.mono` / uppercase date
  style: `AUG 2026 · AI AGENTS`.
- Applies in three places:
  1. Homepage LAB feed preview (`index.html`)
  2. Full LAB listing (`lab/index.html`)
  3. Individual post page header (e.g. `lab/cheap-models-strong-graphs.html`)
- Markup: add a `<span class="mono tag">AI AGENTS</span>` next to
  `.date` in the feed `<li>` and in the post header's date line.
- Existing post "Cheap Models, Strong Graphs" is tagged `AI AGENTS`.
- No filtering, no per-tag pages — purely a visual label for now.

## Out of scope

- Tag-based filtering or dedicated tag pages.
- Linking FOCUS topics to LAB content.
- Any interactivity/JS — stays a static HTML/CSS site (per
  `landing-plan.md` §4, no build step).

## Testing / verification

- Visual check in browser (or via local static server) that:
  - FOCUS section renders between hero and LAB, matches existing type
    scale/spacing, no layout regressions on mobile width.
  - Tag renders correctly next to the date in all three locations without
    wrapping oddly on narrow viewports.
- No automated tests exist for this static site; verification is manual
  render-and-look, consistent with prior work on this project.
