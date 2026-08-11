# FOCUS Page + Research Agent Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the homepage `FOCUS` header into a link to a new standalone
`focus/index.html` page that repeats the FOCUS topics and hosts a living
plan document for a future research agent (page + plan text only — the
agent itself is not built here).

**Architecture:** Static HTML/CSS, no build step, no JS. The new page reuses
`.post`'s existing typography (h1, subtitle, `.body` h2/p/ul/li/code/em) by
nesting an `<article class="post plan">` inside the new page's own section,
with two small CSS overrides (`padding`/`margin-top`) so the reused rules
don't carry their standalone-page-level spacing into this nested context.
No new typographic selectors are introduced — every heading/paragraph/list
rule the plan content needs already exists and applies unchanged via plain
descendant selectors (`.post h1`, `.post .body h2`, etc. match any element
with class `post`, regardless of what other classes it also carries).

**Tech Stack:** Plain HTML5 + CSS (custom properties, no framework/build
step). Verified with `curl` against a local static server
(`python -m http.server 5678 --bind 127.0.0.1` from `C:\a\polozov`) since no
browser automation tool is available in this session.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-11-focus-page-and-agent-plan-design.md`
- The spec's illustrative CSS mechanism (a `.prose` class) is superseded by
  the nested-`.post.plan` approach above — both satisfy the spec's actual
  requirement ("reuse existing typography without duplicating rules"); the
  spec used `.prose` only as an example ("e.g. `.prose`"), not a mandate.
- Plan content copy (headings, paragraphs, list items) must match the
  spec's "Plan content" section **verbatim** — this is finished copy, not a
  draft to rephrase.
- No cards, borders, rounded corners, or accent color — same monochrome,
  flat-text-block system as the rest of the site.
- `focus/index.html` follows `lab/index.html`'s precedent exactly for page
  chrome: `<body class="subpage">`, no `og:` meta tags (only `lab/index.html`
  omits them; article-style pages like the LAB post and the homepage do
  carry them — this new page is a listing/hub page like `lab/index.html`,
  not an article, so it follows that precedent), same footer, and a
  `<a href="../" class="all-posts">← Home</a>` back link in the same
  position (after the section's content, inside `.wrap`).
- Building the research agent itself (any code, scheduler, API calls) is
  explicitly out of scope.
- No git repo issue this time — the repo now exists (initialized in prior
  work on this branch); commit each task normally.
- Local static server expected at `http://127.0.0.1:5678/` — start with
  `python -m http.server 5678 --bind 127.0.0.1` from `C:\a\polozov` if not
  already running (bind explicitly to 127.0.0.1; port 8000 is occupied by
  an unrelated process on this machine, and other binds have hung the TCP
  handshake in this environment before).

---

### Task 1: Create the FOCUS page

**Files:**
- Create: `focus/index.html`
- Modify: `styles.css` (two small additive rule blocks — see Steps 2 and 3)

**Interfaces:**
- Consumes: existing `.post`, `.post .body h2/.num/p/ul/li/code/em`,
  `.section-label`, `.topics`/`.topic-name`/`.topic-gloss`, `.all-posts`
  CSS rules — unchanged, matched via plain descendant selectors.
- Produces: `.post.plan` CSS override class, `#focus.standalone` CSS class,
  both consumed only by `focus/index.html` (Task 2 does not depend on
  these — it only edits `index.html`'s existing `FOCUS` label).

- [ ] **Step 1: Create `focus/index.html`**

Create the file with this exact content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FOCUS — Artem Polozov</title>
  <meta name="description" content="Data viz, full-stack architecture, and AI agent engineering — plus a living plan for a research agent that watches all three.">
  <meta name="color-scheme" content="dark">
  <link rel="stylesheet" href="../styles.css">
</head>
<body class="subpage">

  <section id="focus" class="standalone">
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

      <article class="post plan">
        <h1>A Research Agent for FOCUS</h1>
        <p class="subtitle">
          A living plan for a background agent that watches the three topics
          above so research doesn't compete with writing time.
        </p>

        <div class="body">
          <h2><span class="num">01</span>Goal</h2>
          <p>
            The agent's only job is to read so I don't have to read
            everything myself. Once a week it hands me a short, curated
            list of what actually moved in data viz, full-stack
            architecture, and AI engineering — links and a sentence each,
            nothing published, nothing public. Raw material for LAB posts,
            not a LAB post itself.
          </p>

          <h2><span class="num">02</span>Sources</h2>
          <p>Four kinds of source, each with a different signal-to-noise ratio:</p>
          <ul>
            <li>Web search — broad net, catches whatever isn't already covered below.</li>
            <li>Hacker News — via the public Algolia search API, filtered to each topic's keywords.</li>
            <li>A handful of subreddits per topic — chosen once, revisited later if the signal is bad.</li>
            <li>Blog and RSS feeds — a curated list maintained by hand, the highest-signal source once it exists.</li>
          </ul>

          <h2><span class="num">03</span>Pipeline</h2>
          <p>Five stages, each one a small, replaceable piece:</p>
          <ul>
            <li>Collect — each source connector runs independently and returns a flat list of candidate links.</li>
            <li>Dedupe — every link's URL gets hashed against a store of what's already been sent; only new links continue.</li>
            <li>Summarize &amp; rank — an LLM reads each candidate against the three topic descriptions and returns a one-line summary plus a relevance score; anything below the threshold gets dropped.</li>
            <li>Assemble — surviving items get grouped by topic into a digest, ordered by relevance within each group.</li>
            <li>Deliver — the digest goes out by email on a fixed schedule.</li>
          </ul>

          <h2><span class="num">04</span>Proposed stack</h2>
          <ul>
            <li>A single Python script, run on a schedule rather than a long-lived service — nothing here needs to be always-on.</li>
            <li><code>feedparser</code> for RSS/blog sources, the Hacker News Algolia API and Reddit's public JSON endpoints for the aggregators, a web search API (or Claude's built-in web search) for the broad net.</li>
            <li>A flat JSON file (or SQLite if it outgrows that) holding seen-URL hashes — the whole point of dedupe is state that survives between runs.</li>
            <li>Claude for summarization and relevance scoring — the same model already writing LAB posts, reused for a much smaller job.</li>
            <li>A scheduled GitHub Action or plain cron for the trigger; SMTP or a transactional email API (Resend) for delivery.</li>
          </ul>

          <h2><span class="num">05</span>Cadence &amp; format</h2>
          <p>
            Weekly to start — daily would just move the same reading load
            into more, smaller interruptions. Each digest groups items
            under the three topic headers, five to ten per group, one line
            of summary and a link each. Cadence is the first knob to turn
            if the volume feels wrong in either direction.
          </p>

          <h2>What's still open</h2>
          <ul>
            <li>Daily vs weekly — start weekly, watch whether Friday's digest already feels stale by Wednesday.</li>
            <li>Resurfacing — a link dismissed once shouldn't come back next week just because dedupe only tracks URLs verbatim.</li>
            <li>Where it runs — a scheduled GitHub Action costs nothing and needs no server, but secrets (search API key, email credentials) have to live somewhere.</li>
            <li>Budget — search and LLM calls both cost money per run; weekly cadence keeps this small, but the number should get watched once it's real.</li>
          </ul>

          <h2>Status</h2>
          <p>Planning — not yet built. This page is where the plan lives and changes as it gets built.</p>
        </div>
      </article>

      <a href="../" class="all-posts">← Home</a>
    </div>
  </section>

  <footer>
    <div class="wrap">
      <p class="mono">
        <a href="mailto:hypnosisflow@gmail.com">hypnosisflow@gmail.com</a>
        ·
        <a href="https://github.com/hpnssflw">github.com/hpnssflw</a>
        ·
        © 2026
      </p>
    </div>
  </footer>

</body>
</html>
```

- [ ] **Step 2: Add desktop CSS overrides**

In `styles.css`, in the `/* --- FOCUS --- */` section, immediately after
the existing block:

```css
#focus {
  padding-bottom: 100px;
}
```

insert:

```css
/* Standalone page (/focus/) — needs top air the hero normally provides.
   Same pattern as #lab.standalone. */
#focus.standalone {
  padding-top: 140px;
}
```

Then, in the `/* --- Post --- */` section, immediately after the existing
block:

```css
.post {
  padding: 140px 0 160px;
}
```

insert:

```css
/* The plan article is nested inside #focus.standalone, not a standalone
   page of its own — it doesn't need .post's page-level vertical padding,
   just separation from the topics list above it. */
.post.plan {
  padding: 0;
  margin-top: 96px;
}
```

- [ ] **Step 3: Add mobile CSS overrides**

In `styles.css`, inside the `@media (max-width: 640px)` block, immediately
after the existing:

```css
  #focus {
    padding-bottom: 64px;
  }
```

insert:

```css
  #focus.standalone {
    padding-top: 88px;
  }
```

And immediately after the existing:

```css
  .post {
    padding: 88px 0 96px;
  }
```

insert:

```css
  .post.plan {
    margin-top: 56px;
  }
```

- [ ] **Step 4: Verify the page renders correctly**

Ensure the local server is running (see Global Constraints), then run:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5678/focus/
curl -s http://127.0.0.1:5678/focus/ | grep -c 'topic-name'
curl -s http://127.0.0.1:5678/focus/ | grep -c '<h2>'
curl -s http://127.0.0.1:5678/focus/ | grep -o 'A Research Agent for FOCUS'
```

Expected: `200`, then `3` (three topics), then `7` (five numbered + two
plain h2 sections), then the title string printed once.

Then confirm the existing LAB post page is visually unaffected by the new
`.post.plan` rule (it should not match `.plan`, so nothing changes there):

```bash
curl -s http://127.0.0.1:5678/lab/cheap-models-strong-graphs.html | grep -c 'class="post"'
```

Expected: `1` (the post's own `<article class="post">`, unaffected —
`.post.plan` only applies to elements with both classes).

- [ ] **Step 5: Visual confirmation**

No browser automation tool is available this session. Report to the user
that the page is in place and ask them to open
`http://127.0.0.1:5678/focus/` to confirm spacing between the topics list
and the plan article looks right, and that the LAB post
(`http://127.0.0.1:5678/lab/cheap-models-strong-graphs.html`) still looks
unchanged, on both desktop and a narrow (mobile) viewport width.

- [ ] **Step 6: Commit**

```bash
git add focus/index.html styles.css
git commit -m "Add /focus/ page with research agent plan"
```

---

### Task 2: Link the homepage FOCUS header

**Files:**
- Modify: `index.html:38`

**Interfaces:**
- Consumes: `focus/index.html` existing at `focus/` (created in Task 1) —
  this task only adds a link to it, no shared code/CSS with Task 1.

- [ ] **Step 1: Make the FOCUS label a link**

In `index.html`, replace:

```html
      <p class="section-label">FOCUS</p>
```

with:

```html
      <p class="section-label"><a href="focus/">FOCUS</a></p>
```

(This exactly mirrors the existing `LAB` label two sections below it:
`<p class="section-label"><a href="lab/">LAB</a></p>`.)

- [ ] **Step 2: Verify the link**

```bash
curl -s http://127.0.0.1:5678/ | grep -o '<p class="section-label"><a href="focus/">FOCUS</a></p>'
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5678/focus/
```

Expected: the link markup printed once, then `200`.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "Link homepage FOCUS header to /focus/ page"
```

---

## Self-Review Notes

- Spec coverage: page creation with exact plan copy → Task 1 Step 1. CSS
  reuse without duplication → Task 1 Steps 2-3 (verified: no new
  h1/subtitle/h2/p/ul/li/code/em selectors added — only two small
  padding/margin overrides). Homepage link → Task 2. Out-of-scope items
  (agent code) are simply not built — nothing in either task touches them.
- No placeholders: all markup/CSS is complete and copy-pasteable, plan
  copy matches the spec verbatim.
- Type/name consistency: `.post.plan` and `#focus.standalone` are each
  defined once (Task 1) and referenced only by the markup Task 1 also
  creates — no cross-task naming mismatches to check, since Task 2 doesn't
  touch CSS or the new page.
