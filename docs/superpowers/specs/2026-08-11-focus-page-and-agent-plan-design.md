# FOCUS page + research agent plan

## Purpose

Turn the homepage FOCUS header into a link, the same way LAB already links to
`lab/`. The destination page repeats the FOCUS topics and, below them, hosts
a living plan document for a future background agent that researches the
three FOCUS topics on Artem's behalf. The agent itself is **not** built as
part of this work — only the page and the plan text.

## Site mechanics

- New file `focus/index.html`, mirroring the standalone-page pattern already
  used by `lab/index.html`: same `<body class="subpage">`, same `.wrap`,
  same footer, a `← Home` back link (matching `lab/index.html`'s `← Home`
  link back to `../`).
- Homepage (`index.html`): the `FOCUS` section label becomes a link, exactly
  mirroring the LAB header's existing `<a href="lab/">LAB</a>` pattern:
  ```html
  <p class="section-label"><a href="focus/">FOCUS</a></p>
  ```
- `focus/index.html` structure, top to bottom:
  1. `#focus` standalone section: `.section-label` "FOCUS" + the same
     `.topics` list (3 items) as the homepage, verbatim copy.
  2. Below the topics, the plan content (see below) — reuses the same
     typographic idiom as a LAB post body (`h2` section headers with an
     optional `<span class="num">NN</span>` prefix, `p`, `ul`/`li`).
  3. `← Home` back link, then the shared footer.
- CSS reuse: `.post .body h2/h2 .num/p/ul/li/code/em` currently exist only
  under the `.post .body` selector (`styles.css:465-508`). This work
  generalizes those rules to a shared class (e.g. `.prose`) applied to both
  `.post .body` (LAB posts) and the new plan container on `focus/index.html`,
  so the two features don't duplicate the same CSS. This is a rename/reuse
  of existing rules, not new styling.

## Plan content (verbatim copy for `focus/index.html`)

```
<h1>A Research Agent for FOCUS</h1>
<p class="subtitle">
  A living plan for a background agent that watches the three topics above
  so research doesn't compete with writing time.
</p>

<h2><span class="num">01</span>Goal</h2>
<p>
  The agent's only job is to read so I don't have to read everything myself.
  Once a week it hands me a short, curated list of what actually moved in
  data viz, full-stack architecture, and AI engineering — links and a
  sentence each, nothing published, nothing public. Raw material for LAB
  posts, not a LAB post itself.
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
  Weekly to start — daily would just move the same reading load into more,
  smaller interruptions. Each digest groups items under the three topic
  headers, five to ten per group, one line of summary and a link each.
  Cadence is the first knob to turn if the volume feels wrong in either
  direction.
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
```

This copy is final for the initial version of the page. It is explicitly a
**living document** — the "Status" section exists so it can be edited in
place as the actual agent gets built later, without needing a new spec/plan
cycle for small text updates to this page.

## Out of scope

- Building the agent itself (any code, scheduler, API integration).
- Any interactivity/JS on `focus/index.html` — stays static HTML/CSS.
- Deciding cadence/sources/stack for real — the plan documents a proposal,
  not a locked decision; those choices get revisited when the agent is
  actually built.

## Testing / verification

- Same as prior work on this site: no automated test suite. Verify via
  `curl` against a locally served copy that `focus/index.html` returns 200
  and contains the expected headings/links, that the homepage's `FOCUS`
  label is now a link to `focus/`, and that the shared prose CSS renders
  identically on both the LAB post and the new FOCUS page (no visual
  regression on the existing LAB post from the class rename/generalization).
- Manual visual check by the user, same as prior tasks, since no browser
  automation tool is available in this session.
