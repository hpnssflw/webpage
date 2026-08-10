# FOCUS Section + LAB Topic Tags Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a FOCUS section to the homepage listing Artem's three areas of
interest, and a topic-tag scheme applied to LAB posts wherever their date
appears.

**Architecture:** Static HTML/CSS site, no build step, no JS. Changes are
markup additions to `index.html`, `lab/index.html`, and
`lab/cheap-models-strong-graphs.html`, plus new CSS rules in `styles.css`
that reuse the existing type scale and spacing tokens. No new files.

**Tech Stack:** Plain HTML5 + CSS (custom properties, no framework/build
step). Verified with `curl` against a local static server (Python's
`http.server`) since no browser automation tool is available in this
session.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-10-focus-section-and-lab-tags-design.md`
- No cards, borders, or rounded corners — flat text blocks only (site design
  token rule, `landing-plan.md` §1).
- Case system is strict: UPPERCASE for meta/chrome (labels, dates, tags,
  nav), lowercase for content (titles, prose) — enforced via CSS
  `text-transform`, markup keeps correct source casing (`styles.css:5-10`).
- No accent color — monochrome only (`--bg`, `--text`, `--text-strong`,
  `--muted` from `styles.css:13-17`).
- Fixed topic set, exact copy (verbatim from spec):
  - `Data Viz` — "BI dashboards, browser graphics, render-engine performance."
  - `Full-Stack Architecture` — "trends, architectures, best practices and patterns across the modern web stack."
  - `AI Agents & Engineering` — "trends, architectures and patterns for building and running agents in production."
  - Tag short forms: `DATA VIZ`, `FULL-STACK`, `AI AGENTS`
- This project directory (`C:\a\polozov`) has no git repository initialized.
  Tasks below have no commit step; verify each task by re-reading the file
  and checking it with `curl` against the local server instead.
- Local static server is expected to run at `http://127.0.0.1:5678/` (start
  with `python -m http.server 5678 --bind 127.0.0.1` from `C:\a\polozov` if
  not already running — port 8000 is occupied by an unrelated process on
  this machine, and binding to `0.0.0.0`/`::` has previously hung the TCP
  handshake in this environment, so bind explicitly to `127.0.0.1`).

---

### Task 1: FOCUS section on the homepage

**Files:**
- Modify: `index.html:34-35` (insert new section between `</section>` closing
  `#hero` and `<section id="lab">`)
- Modify: `styles.css` (append new rule block after the LAB feed rules,
  i.e. after `styles.css:367` `.all-posts { ... }`, before
  `/* --- Post ------------------------------------------------------ */`)

**Interfaces:**
- Produces: `#focus` section with class `.topics` list, items using
  `.topic-name` / `.topic-gloss` spans. Task 2 does not depend on this
  markup, but keep the class names exactly as below since they're
  referenced in this task's own CSS.

- [ ] **Step 1: Insert the FOCUS section markup**

In `index.html`, replace:

```html
  </section>

  <section id="lab">
```

with:

```html
  </section>

  <section id="focus">
    <div class="wrap">
      <p class="section-label">FOCUS</p>
      <ul class="topics">
        <li>
          <span class="topic-name">Data Viz</span>
          <span class="topic-gloss">BI dashboards, browser graphics, render-engine performance.</span>
        </li>
        <li>
          <span class="topic-name">Full-Stack Architecture</span>
          <span class="topic-gloss">trends, architectures, best practices and patterns across the modern web stack.</span>
        </li>
        <li>
          <span class="topic-name">AI Agents &amp; Engineering</span>
          <span class="topic-gloss">trends, architectures and patterns for building and running agents in production.</span>
        </li>
      </ul>
    </div>
  </section>

  <section id="lab">
```

- [ ] **Step 2: Add FOCUS section CSS**

In `styles.css`, after the `.all-posts { ... }` block (ends at line 367)
and before the `/* --- Post --- */` comment, insert:

```css
/* --- FOCUS ------------------------------------------------------ */

#focus {
  padding-bottom: 100px;
}

.topics {
  list-style: none;
  margin: 0;
  padding: 0;
}

.topics li + li {
  margin-top: 32px;
}

.topic-name {
  display: block;
  font-size: 1rem; /* 16 — matches .feed .title */
  font-weight: var(--w-normal);
  letter-spacing: 0;
  color: var(--text-strong);
  line-height: 1.45;
  margin-bottom: 8px;
  text-transform: lowercase;
}

.topic-gloss {
  display: block;
  font-size: 0.8125rem; /* 13 — matches .feed .excerpt */
  color: var(--muted);
  max-width: 34em;
  text-transform: lowercase;
}
```

- [ ] **Step 3: Verify the section renders in the served HTML**

Ensure the local server is running (see Global Constraints), then run:

`curl -s http://127.0.0.1:5678/ | grep -A2 'id="focus"'`

Expected output includes `<section id="focus">` followed by the `.wrap`
div and `FOCUS` label line.

Then run:

`curl -s http://127.0.0.1:5678/ | grep -c 'topic-name'`

Expected output: `3`

- [ ] **Step 4: Visual confirmation**

No browser automation tool is available this session. Report to the user
that the section is in place and ask them to open
`http://127.0.0.1:5678/` themselves to confirm spacing/line-length look
right on both desktop and a narrow (mobile) viewport width, since this
step can't be verified programmatically.

---

### Task 2: LAB topic tags (feed + post page)

**Files:**
- Modify: `index.html:41-45` (LAB feed `<li>` for the existing post)
- Modify: `lab/index.html:17-23` (same feed `<li>`, duplicated markup)
- Modify: `lab/cheap-models-strong-graphs.html:18` (post header date line)
- Modify: `styles.css` (append `.tag` rule near `.feed .date`, after
  `styles.css:335` closing brace of `.feed .date { ... }`, before
  `.feed .title { ... }`)

**Interfaces:**
- Consumes: nothing from Task 1 — independent of the FOCUS section markup.
- Produces: `.mono.tag` span usable anywhere a date appears; established
  pattern `<span class="mono date">AUG 2026</span> <span class="mono
  tag">AI AGENTS</span>` for future LAB posts to copy.

- [ ] **Step 1: Add the tag CSS rule**

In `styles.css`, immediately after the `.feed .date { ... }` block (ends
at line 335) and before `.feed .title { ... }`, insert:

```css
.tag {
  color: var(--muted);
}

.feed .date + .tag,
.post .date + .tag {
  margin-left: 8px;
}
```

- [ ] **Step 2: Tag the feed entry on the homepage**

In `index.html`, replace:

```html
        <li>
          <a href="lab/cheap-models-strong-graphs.html">
            <span class="mono date">AUG 2026</span>
            <span class="title">Cheap Models, Strong Graphs</span>
```

with:

```html
        <li>
          <a href="lab/cheap-models-strong-graphs.html">
            <span class="mono date">AUG 2026</span><span class="mono tag">AI AGENTS</span>
            <span class="title">Cheap Models, Strong Graphs</span>
```

- [ ] **Step 3: Tag the feed entry on the LAB index page**

In `lab/index.html`, replace:

```html
        <li>
          <a href="cheap-models-strong-graphs.html">
            <span class="mono date">AUG 2026</span>
            <span class="title">Cheap Models, Strong Graphs</span>
```

with:

```html
        <li>
          <a href="cheap-models-strong-graphs.html">
            <span class="mono date">AUG 2026</span><span class="mono tag">AI AGENTS</span>
            <span class="title">Cheap Models, Strong Graphs</span>
```

- [ ] **Step 4: Tag the post page header**

In `lab/cheap-models-strong-graphs.html`, replace:

```html
      <p class="mono date">AUG 2026</p>
```

with:

```html
      <p class="mono date">AUG 2026<span class="tag">AI AGENTS</span></p>
```

- [ ] **Step 5: Verify tags appear in all three pages**

Run:

```bash
curl -s http://127.0.0.1:5678/ | grep -o 'AI AGENTS'
curl -s http://127.0.0.1:5678/lab/ | grep -o 'AI AGENTS'
curl -s http://127.0.0.1:5678/lab/cheap-models-strong-graphs.html | grep -o 'AI AGENTS'
```

Expected: each command prints `AI AGENTS` at least once (homepage and
`/lab/` once each from the feed item, post page once from the header).

- [ ] **Step 6: Visual confirmation**

Ask the user to check `http://127.0.0.1:5678/` and
`http://127.0.0.1:5678/lab/cheap-models-strong-graphs.html` to confirm the
tag doesn't wrap awkwardly next to the date at mobile width, since no
browser automation tool is available this session to check this
programmatically.

---

## Self-Review Notes

- Spec coverage: FOCUS section (3 topics, homepage placement, label+gloss
  format) → Task 1. Tag scheme (3 short forms, next to date, 3 locations,
  existing post tagged `AI AGENTS`) → Task 2. Out-of-scope items (filtering,
  linking, JS) are simply not built — nothing in either task introduces
  them.
- No placeholders: all markup/CSS is complete and copy-pasteable.
- Type/name consistency: `.topic-name`/`.topic-gloss` only used in Task 1;
  `.tag` only used in Task 2 — no cross-task naming collisions to check.
