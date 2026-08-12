# Run panel — local monitoring and control for the research agent

## Purpose

A local panel for watching the research agent work and for tuning it. Two
jobs, in order of how much they matter:

1. **Answer "why did this item not make the digest?"** in one glance. The
   agent drops far more candidates than it keeps, and every tuning decision —
   widen the window, lower the threshold, drop a subreddit — depends on
   seeing which filter did the dropping and by how much.
2. **Show the pipeline running.** Useful during the edit-YAML-and-re-run
   loop, and the basis for a public showcase later.

The panel renders the JSONL event stream produced by the agent (see
`2026-08-12-research-agent-design.md` § Event stream). It parses that stream
and nothing else — it does not import the agent's pipeline modules, and it
does not reimplement any filtering logic. Every number it shows traces to an
event the agent emitted.

A later, separate piece of work turns the same renderer into a public replay
on the site. This spec builds the local tool and states what the public
version will require, but does not build it.

## Ordering

This depends on `2026-08-12-research-agent-design.md` TASK-004 (`events.py`
and the dry run), because before that there is no stream to render. It does
not depend on the agent being finished — a panel over an HN-only dry run is
already useful, and is the fastest way to validate that the event schema is
rich enough.

## Server

```
python -m agent panel
```

Starts an HTTP server bound explicitly to `127.0.0.1:5679`.

Port 5679 rather than 5678, which `CLAUDE.md` reserves for serving the static
site — the two want to run at the same time when work touches both. Port 8000
is occupied on this machine by an unrelated process.

**The bind address is load-bearing, not incidental.** `POST /run` starts a
subprocess with no authentication of any kind. Binding anything other than
`127.0.0.1` would expose arbitrary process execution to the network. There is
no auth layer and none is planned, because the correct fix is the bind
address rather than a login form on a single-user local tool.

| Method | Path              | Behaviour |
|--------|-------------------|-----------|
| `GET`  | `/`               | The page — a single self-contained HTML file |
| `GET`  | `/runs`           | JSON list of run ids, newest first, with summary counts |
| `GET`  | `/runs/<run_id>`  | That run's JSONL, verbatim |
| `GET`  | `/events/stream`  | SSE; tails the active run's JSONL, one event per message |
| `POST` | `/run`            | Starts a run; body `{"dry_run": bool, "overrides": {…}}` |

`stdlib http.server` with a threading mixin. No framework, no dependency
beyond what the agent already installs.

`POST /run` returns immediately with the new `run_id`; progress arrives over
SSE. A second `POST /run` while one is active is rejected with 409 rather
than queued — two concurrent runs would interleave writes to `state.json`.

## The page

One HTML file. Vanilla JS, inline CSS, no framework, no build step.

This is not the static site and `CLAUDE.md`'s no-JS rule does not apply to it
— but the single-file constraint is deliberate for a different reason: it
makes the public replay a data-source swap rather than a rewrite. The page
reads its events from either SSE or an inlined JSONL blob, decided by one
switch at the top. Everything downstream of that switch is shared.

### Primary view: the funnel

Per topic, with a per-source breakdown available:

```
AI Agents & Engineering
collected 127 → dated 119 → in-window 44 → new 23 → scored ≥6: 19 → sent 8
                     ↓8          ↓75          ↓21        ↓4         ↓11
                  undated    outside      seen      below      over
                                                  relevance   max_items
```

Each `↓` is clickable and expands to the dropped items with their `detail`
payload — published date against the window, score against the threshold —
so the reason is visible without opening the JSONL.

The funnel is the primary view because it maps one-to-one onto the tuning
decisions. A large `outside_window` count means `max_age_days` is too tight;
a large `seen` count means the sources are recycling; a large
`below_relevance` count means the keywords are pulling in noise.

### Secondary view: the event log

Chronological, filterable by stage, source, and topic. What the funnel
aggregates, in raw form. Useful when the funnel says something surprising and
the aggregate is hiding the cause.

### Run history

`/runs` backs a list of past runs with their funnel totals, so week-over-week
drift is visible — a source whose yield is decaying, or a threshold that
stopped letting anything through.

## Control: the panel proposes, the YAML disposes

Threshold controls (`max_age_days`, `min_relevance`, `min_points`) apply as
**overrides for a single dry run**. They are passed in the `POST /run` body
and never written to a topic file.

To make a change permanent, edit the YAML by hand.

This is a deliberate constraint rather than a missing feature. Round-tripping
YAML through a UI strips comments, produces noisy git diffs, and quietly
makes the panel the source of truth instead of the files chosen as the
control surface in the agent spec. The same principle governs
`suggest-keywords`: the tool recommends, the human commits.

The panel does show current effective config per topic, read-only, so there
is no guessing about which value an override is departing from.

## Public replay — requirements, not built here

The eventual site version renders a recorded run instead of a live one: same
page, `source: "inline"` instead of `source: "sse"`, with a JSONL blob
embedded at build time.

Two things must exist before anything is published:

- **A redaction pass.** A run record contains the full source configuration —
  every subreddit, feed URL, watched repo, and search query. That is a more
  complete picture of what Artem reads than he may want public. An export
  command must produce a sanitized bundle, with the redaction list stated
  explicitly in config rather than inferred.
- **An explicit decision to add JS to the static site.** `CLAUDE.md` states
  the site is deliberately plain HTML/CSS with no build step. The replay page
  breaks that. It is a reasonable rule to break for one page, but it is a
  decision to make on purpose, not a side effect of this work.

Neither is in scope here.

## Out of scope

- The public replay page, the redaction pass, and the export command.
- Authentication, TLS, and any non-loopback binding.
- Editing topic YAML from the panel.
- Charts beyond the funnel. Run history is a list of numbers; if trends
  become genuinely hard to read, that earns its own consideration later.
- Any change to the agent's pipeline logic. If the panel cannot show
  something, the fix is a richer event in the agent spec, not a computation
  in the panel.

## Testing / verification

No automated test suite, consistent with the rest of the repo.

- **Renderer correctness** — the funnel is verified against a recorded dry-run
  JSONL by checking that each stage's inputs minus its drops equals its
  outputs, and that the totals match the counts the terminal renderer prints
  for the same run. The two renderers disagreeing means one is wrong, which
  is the point of having both.
- **Live streaming** — verified by starting a dry run from the panel and
  confirming events appear during the run rather than in one batch at the
  end.
- **Overrides** — verified by running one topic twice, once with
  `max_age_days` overridden downward, and confirming the `outside_window`
  count rises while the topic YAML on disk is byte-identical afterward.
- **The bind address** — verified by confirming the server does not answer on
  the machine's LAN address. This is the one check that must not be skipped.
- Visual check by the user, as with prior work on this repo.

## Open questions

- Whether the event log stays useful once the funnel drill-down exists, or
  becomes redundant. Cheap to keep, cheap to remove later.
- Whether run history wants retention limits. `agent/runs/` grows one file
  per run; at weekly cadence that is ~52 small files a year, which is not a
  problem for years. Revisit if the dry-run loop generates a lot more.
