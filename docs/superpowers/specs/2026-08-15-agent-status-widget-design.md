# Agent status widget — live preview + public dashboard

## Purpose

Make the research agent's activity visible on the public site: a small
terminal-styled preview widget on the homepage, and a fuller live dashboard
on `researcher/agent.html`, both reading from data the agent itself produces
every run. The point is proof — anyone looking at the site can see the agent
is real and currently running, not just described.

**Skill showcased: production LLM pipeline engineering, not just "called an
API."** The specific things worth a visitor noticing — and what the
dashboard should make legible, not just decorative — are: batched ranking
calls validated against an expected schema before use, a retry-then-
per-candidate-fallback path when validation fails twice, a cost-aware model
choice (DeepSeek, chosen for what ranking quality costs at this volume), and
a full audit trail where every kept-or-dropped decision traces to an event.
The dashboard's funnel and ticker exist to make that last point visible,
not just to look busy.

## Supersedes

This spec knowingly revises decisions made in two earlier, already-shipped
specs. Both changes are deliberate, not oversights:

- **`2026-08-12-research-agent-design.md` § Build order** said *"Scheduling
  is Windows Task Scheduler, not a GitHub Action... this repo has no GitHub
  remote configured."* This spec sets up a GitHub remote and moves scheduling
  to GitHub Actions instead, because a client-fetched public widget needs the
  agent's output reachable over HTTP without Artem's machine being the host.
  Windows Task Scheduler remains a fine mechanism for `--dry-run` tuning
  sessions; it is not what the public widget reads from.
- **`2026-08-12-research-agent-design.md` § Out of scope** said *"changing
  the three topics or the weekly cadence"* was out of scope. This spec
  changes the collection/ranking cadence from weekly to every 4 hours (see
  § Scheduling). The three topics are unchanged.
- **`2026-08-12-run-panel-design.md` § Public replay** described the future
  public version as a **build-time embedded JSONL snapshot** (`source:
  "inline"`), refreshed only when Artem republishes the site, and called for
  an explicit redaction pass over run records before anything public. This
  spec instead uses a **live-fetched aggregate JSON file**, refreshed by
  GitHub Actions every 4 hours independent of when Artem next touches the
  site. Redaction is handled structurally rather than by a separate export
  command (see § Redaction, below) — the aggregate file this spec defines
  never contains topic `keywords`, `sources`, subreddit lists, feed URLs, or
  search queries; it contains only candidate titles/URLs/scores, which are
  already public HN content, and counts.
- **`2026-08-15-report-storage-and-dashboard-design.md`** — a parallel
  session's spec for local-only storage (SQLite) and a local-only
  dashboard, written before that session saw this one. Superseded outright
  by this spec for scheduling and dashboard visibility. Two things from it
  were merged forward rather than discarded: the pending-queue re-ranking
  fix in § Email delivery decoupling below, and a note that
  `agent/store.py`'s SQLite design is the reference to reach for if the
  local run panel later wants queryable history beyond `status.json`'s
  capped rolling windows.
- The run panel itself (`python -m agent panel`, local-only, SSE-driven) is
  unaffected and not built by this spec. It remains the right tool for the
  edit-YAML-and-re-run tuning loop; this spec's widget is a separate,
  lighter path that does not depend on the panel existing.

## Scheduling & data architecture

- `agent/main.py`'s `run_real` (already shipped, Task 6) runs on a GitHub
  Actions cron trigger: `0 */4 * * *` — every 4 hours, 6 runs/day.
- This is the first thing in this repo to need a GitHub remote. `CLAUDE.md`'s
  "no GitHub remote configured" note describes the state before this spec;
  setting one up is in scope here.
- The workflow checks out two refs:
  - **`master`** — the agent code, read-only for this job.
  - **`agent-data`** (new orphan branch, no shared history with `master`) —
    holds everything a run produces or consumes: `agent/state.json` (dedupe
    store), `agent/pending.json` (items ranked-and-kept but not yet
    emailed), and `agent/status.json` (the public aggregate — see § Data
    contract). All three are gitignored on `master` as before; on
    `agent-data` they are the entire point of the branch.
- After each run, the workflow commits the updated three files to
  `agent-data` and pushes. `master` is untouched by this cycle — it only
  changes when Artem edits code or docs, exactly as today.
- The site fetches `status.json` client-side via
  `raw.githubusercontent.com/<user>/<repo>/agent-data/agent/status.json` —
  a public JSON file on a public branch, no server, no API.

### Redaction

`status.json` is built by a new small function (see § Module layout) that
reads only: the latest run's JSONL event stream, `pending.json`'s count, and
`state.json`'s aggregate streak bookkeeping. It never reads `TopicConfig.
sources` or `.keywords`. This is enforced by construction — the exporter
function's input types don't include `TopicConfig` at all, only `Candidate`,
`Drop`, and plain counts — so there is no field to accidentally leak.

## Email delivery decoupling

Collection/ranking now runs 4x more often than delivery should. `run_real`
changes:

1. Each run still collects → date-guards → dedupes → ranks, exactly as
   shipped. Newly above-threshold items are **appended to
   `agent/pending.json`** instead of being emailed immediately.
   `dedupe.mark_sent` is **not** called at this point — an item isn't a
   duplicate until it's actually been emailed, and `filter_seen`'s
   `times_sent > 0` check depends on that staying true.

   **Dedup against the pending queue itself, before ranking.** Without
   this, an item sitting in `pending.json` waiting for the 24h email
   gate is not caught by `filter_seen` (its `times_sent` is still 0), so
   HN keeps re-surfacing it, and it gets re-sent to DeepSeek for ranking
   on every subsequent 4h cycle until the gate finally fires — up to 6×
   redundant paid ranking calls for the same item over 24 hours. Fix:
   after `filter_seen`, drop any candidate whose URL hash is already
   present in `pending.json` *before* the ranking call, using the same
   `reason="seen"` drop event `filter_seen` already emits (`detail`
   distinguishes `{"times_sent": N}` from `{"pending_since": "..."}` so
   the two cases stay visible in the event stream without extending the
   closed drop-reason set). Ranking only ever runs once per item, at
   the moment it first crosses the relevance threshold.
2. After updating `pending.json`, `run_real` checks whether email is due:
   `last_email_at` (stored in `pending.json` alongside the queue) is more
   than `email_cadence_hours` (default 24, in `defaults.yaml`) in the past,
   **and** the queue is non-empty. If both hold: build the digest from the
   *entire* pending queue (across all runs since the last email, not just
   this run), send it, call `dedupe.mark_sent` on every item in it, clear
   the queue, stamp `last_email_at` to now.
3. If email isn't due, the run ends after updating `pending.json` and
   `status.json` — no SMTP call.
4. Every run, regardless of whether it emailed, emits a terminal
   `writer.emit("run", "complete", detail={...})` event. This is what the
   status exporter uses to compute `streak` (see below) and is a small,
   independently useful addition to the event stream regardless of this
   spec — the run panel can use it too.

This means `digest.py` and the `RANK_SYSTEM_PROMPT` string in
`summarize.py` need their "weekly research digest" wording updated — they
no longer describe an accurate cadence. Reword to just "research digest"
(drop "weekly").

## Data contract: `agent/status.json`

```jsonc
{
  "updated_at": "2026-08-15T14:00:03Z",   // this run's timestamp, whether or not it completed cleanly
  "cadence_hours": 4,
  "streak": 11,                            // consecutive runs whose JSONL contains a "run"/"complete" event; resets to 0 on any run that doesn't
  "last_email_at": "2026-08-15T09:00:00Z",
  "email_cadence_hours": 24,
  "pending_email_count": 7,                // agent/pending.json's current size, across all topics

  "topics": [
    { "slug": "ai-agents", "name": "AI Agents & Engineering", "collected": 32, "kept": 5 },
    { "slug": "data-viz", "name": "Data Viz", "collected": 18, "kept": 0 },
    { "slug": "full-stack", "name": "Full-Stack Architecture", "collected": 24, "kept": 2 }
  ],

  "funnel": {                              // per-topic stage counts, this run only — feeds the dashboard's funnel bars
    "ai-agents": { "collected": 32, "in_window": 21, "new": 9, "kept": 5 },
    "data-viz": { "collected": 18, "in_window": 13, "new": 4, "kept": 0 },
    "full-stack": { "collected": 24, "in_window": 17, "new": 6, "kept": 2 }
  },

  "recent_events": [                       // last ~15 kept/dropped items across recent runs, newest first — feeds the dashboard ticker
    { "ts": "2026-08-15T14:00:01Z", "verdict": "kept", "source": "hn", "topic": "ai-agents",
      "title": "Production agent evals, one year in", "score": 9 },
    { "ts": "2026-08-15T14:00:01Z", "verdict": "drop", "source": "hn", "topic": "full-stack",
      "title": "React 19 notes", "reason": "outside_window" }
  ],

  "run_history": [                         // capped at 24 entries, oldest dropped when a new one is appended — feeds the sparkline
    { "ts": "2026-08-15T10:00:02Z", "kept": 3 },
    { "ts": "2026-08-15T14:00:03Z", "kept": 7 }
  ]
}
```

`kept` replaces the `sent` name used in earlier drafts of this design —
"sent" was ambiguous between "survived ranking this run" and "actually
emailed," and those are now different things (§ Email delivery decoupling).

## Homepage widget

Placement: on `index.html`, directly under the existing RESEARCHER topics
list, before the current "the plan" link. Links to `researcher/agent.html`.

Content (validated against mockups — "everything that fits" density):

```
● agent online   runs every 4h · streak 11
schema-validated LLM ranking · full audit trail
▂▃▅▁▄▆█▅▃▇▉▄▃▅▆▁▃▅▇█   last 24 runs
─────────────────────────
ai agents   5/32   data viz  0/18   full-stack  2/24
next check  00:42:11         view dashboard →
```

- The tagline (`schema-validated LLM ranking · full audit trail`) is a
  static string, not derived from `status.json` — it names the skill this
  widget is meant to demonstrate (§ Purpose), not a live metric.
- Dot color: lime (`#7CFC00`) when `updated_at` is within `2 × cadence_hours`
  of now; red (`#ff4d4d`) otherwise, label changes to "stale".
- Sparkline: one glyph per `run_history` entry, height ∝ `kept`, red when
  `kept == 0` for that run.
- Per-topic counts: `kept/collected` from `status.json.topics`.
- "next check" countdown: computed client-side from
  `updated_at + cadence_hours`, ticking down with `setInterval`. Not exact
  (Actions cron has scheduling jitter) — labelled as an estimate, not a
  guarantee.
- Whole card is a link (`<a>` wrapping the block), not just the "view
  dashboard →" text.

Fetch failure or missing `status.json` (e.g. before the first Action run
lands): render a muted fallback line — `agent status unavailable` — no dot,
no crash, no stale error styling.

## Dashboard section — `researcher/agent.html`

Dashboard-first: the live section leads the page, the existing narrative
plan content (unchanged) follows below it.

```
● AGENT ONLINE                runs every 4h · streak 11
Building production AI pipelines: schema-validated LLM
calls, automatic fallback, full audit trail of every
decision the ranker makes.
▂▃▅▁▄▆█▅▃▇▉▄▃▅▆▁▃▅▇█           last 24 runs
─────────────────────────────────────
AI AGENTS   ████████░░░░ 9/32   kept 5
DATA VIZ    ███░░░░░░░░░ 4/18   kept 0
FULL-STACK  ██████░░░░░░ 6/24   kept 2
─────────────────────────────────────
08:12:05  KEPT  ai-agents   "Production agent evals..."
08:12:04  DROP  full-stack  "React 19 notes"   outside_window
08:12:03  KEPT  data-viz    "WebGL instancing..."
...

[existing "a research agent" narrative content, unchanged]
```

- The description line under the status header is static copy naming the
  skill this project demonstrates (§ Purpose) — not derived from
  `status.json`. The funnel and ticker below it are the evidence for that
  claim: every row is traceable to an actual event the agent emitted, not
  set dressing.
- Status header + sparkline: same data and stale logic as the homepage
  widget, just larger.
- Per-topic funnel: bars per topic showing `funnel[slug]`'s four stages
  (`collected → in_window → new → kept`), matching the terminology the
  local run panel already uses so the two don't drift apart.
- Live ticker: renders `recent_events`, color-coded by `verdict` (`kept` =
  lime, `drop` = red), reason shown for drops.
- All three sourced from the same single `status.json` fetch — no separate
  requests per section.

## Visual design

Terminal aesthetic layered on top of the existing monochrome system in
`styles.css`: `JetBrains Mono` (already a token, `--font-mono`), dark panel
background (`#141414`, slightly darker than the page's `#202020` so the
widget reads as its own surface), lime (`#7CFC00`) for positive/online
states, red (`#ff4d4d`) for stale/dropped states.

This is a second deliberate break from the site's monochrome palette — the
first being the hero thesis's italic + full-strength color
(`styles.css` line 256's comment: *"the only accent the monochrome palette
allows"*). That comment becomes inaccurate once this ships and should be
updated to describe both accents, not silently left wrong.

## Client-side JS

New, small, vanilla — no framework, per `CLAUDE.md`'s constraint on
everything else this JS doesn't touch. This is an explicit, on-purpose
exception to "no JS," made by this spec, the same way the run-panel spec
called out its own JS as a deliberate exception for the local panel.

- One shared file, `assets/agent-widget.js`, included by both `index.html`
  and `researcher/agent.html`.
- `fetch()`s `status.json` once on page load. No polling — at a 4-hour
  server-side cadence, a page open long enough for polling to matter is not
  a real scenario worth the complexity.
- Renders into a `<div id="agent-widget">` / `<div id="agent-dashboard">`
  mount point each page already has in its HTML; the JS fills it in,
  doesn't construct the page shell.
- The countdown and stale-check re-evaluate every second via
  `setInterval`, purely client-side arithmetic against the one fetched
  `updated_at` — no repeated network calls.

## Module layout (new/changed files)

```
.github/workflows/
└── agent-run.yml          # cron trigger, checks out master + agent-data, runs the agent, commits status

agent/
├── main.py                 # run_real: pending-queue + email-cadence-gate changes; emits "run"/"complete"
├── status_export.py        # NEW — builds status.json from a run's JSONL + pending.json + prior run_history
├── digest.py                # reword "weekly" out of the subject/body
├── summarize.py              # reword RANK_SYSTEM_PROMPT's "weekly research digest"
├── pending.json              # NEW — gitignored on master, tracked on agent-data
├── state.json                 # unchanged shape, now also tracked on agent-data
└── status.json                 # NEW — gitignored on master, tracked on agent-data (this is what the site fetches)

assets/
└── agent-widget.js         # NEW — fetch + render, shared by both pages

index.html                  # homepage widget markup + mount point
researcher/agent.html       # dashboard section + mount point, above existing narrative
styles.css                  # .agent-widget / .agent-dashboard rules, lime/red tokens
```

## Out of scope

- The local run panel (`python -m agent panel`) — unchanged, separate spec,
  not built or modified here.
- Changing the three topics.
- Any source beyond HN (Reddit/RSS/releases/web search remain TASK-007+ in
  the original plan, unaffected by this spec).
- Historical backfill — `status.json`'s `run_history` starts empty and
  fills up over the first 24 runs (4 days) after this ships; no attempt to
  reconstruct history from old local `agent/runs/*.jsonl` files.
- Real-time push (WebSockets/SSE) to the public widget. Fetch-on-load
  against a file that updates every 4 hours is enough; the local panel
  already covers true live-streaming for the tuning loop.

## Testing / verification

No automated test suite, consistent with the rest of the repo.

- **`status_export.py`** — verified against a recorded `--dry-run` JSONL by
  checking the produced `funnel` counts match what the terminal renderer
  prints for the same file, the same cross-check method the run-panel spec
  uses for its own renderer.
- **The pending-queue / email-gate logic** — verified by running `run_real`
  twice in a row with `email_cadence_hours` temporarily set low, confirming
  the first run populates `pending.json` and sends nothing, and the second
  run (past the cadence) sends the combined queue and clears it.
- **The GitHub Actions workflow** — verified by a manual `workflow_dispatch`
  run before the cron trigger is trusted, checking `agent-data` gets the
  expected three files committed and `master` is untouched.
- **The widget JS** — verified by pointing `fetch()` at a local sample
  `status.json` (via the existing `python -m http.server 5678` flow) and
  confirming the dot color, sparkline, and countdown all render correctly;
  then by deliberately editing `updated_at` to be old and confirming the
  dot flips to red.
- **Fetch failure** — verified by pointing the widget at a 404 URL and
  confirming the fallback line renders instead of a broken page.
- Visual check by Artem, as with prior work on this repo.

## Open questions

- Whether `email_cadence_hours: 24` is the right rollup interval, or
  whether it should itself be configurable per how often the pending queue
  actually fills up in practice. Revisit after a week of real 4h runs.
- Whether GitHub Actions' free-tier minutes comfortably cover 6 runs/day
  long-term, or need watching as the agent grows more sources later.
- Whether `agent-data`'s history should ever be pruned/squashed — an orphan
  branch getting a commit every 4 hours accumulates ~2,190 commits/year.
  Cheap to ignore for now; revisit if branch size becomes noticeable.
