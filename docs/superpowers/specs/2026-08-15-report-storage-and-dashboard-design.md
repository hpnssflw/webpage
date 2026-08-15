# Report storage and dashboard — replacing email delivery for now

> **Superseded by `2026-08-15-agent-status-widget-design.md`.** That spec
> (a parallel session, committed to master while this one was in
> progress) moves scheduling to GitHub Actions and makes the dashboard
> public, on the live site, rather than the local-only design below. This
> document is kept for its analysis, not as a build target. Two things
> from here were merged forward into the accepted spec rather than lost:
>
> - The pending-queue re-ranking bug this document's review surfaced (an
>   item waiting for the 24h email rollup gets re-collected and
>   re-ranked by DeepSeek every 4h cycle, since `mark_sent` is
>   deliberately deferred) — patched in the accepted spec's § Email
>   delivery decoupling.
> - The case for durable, queryable per-item history: the accepted
>   spec's `status.json` only keeps a capped rolling window
>   (`run_history`: 24 entries, `recent_events`: ~15). Full history is
>   still recoverable from `agent-data`'s git log, just not
>   conveniently queryable. If the local run panel (out of scope in both
>   specs) later wants real querying — filter by topic, date range,
>   score — the `agent/store.py` / SQLite design below is the reference
>   for that, whenever that panel work happens.

## Purpose

`run_real`'s final stage was designed to email a digest via SMTP
(`agent/deliver.py`, wired in the Task 6 build). SMTP credentials aren't
set up yet, and the live-send verification was deferred rather than run.
Separately, the goal is now to run the real pipeline unattended every 4
hours via Windows Task Scheduler — an unattended email failure every 4
hours (crashing on missing SMTP env vars whenever there's something to
send) is worse than not having delivery at all.

This spec replaces the delivery step for now: ranked digest items get
stored in a local SQLite database instead of emailed, and a small local
dashboard (folded into the already-speced, not-yet-built run panel) lets
them be browsed. Email isn't removed — `agent/deliver.py` stays as-is,
tested and working — `run_real` just doesn't call it right now.

## Relationship to the run-panel spec

`docs/superpowers/specs/2026-08-12-run-panel-design.md` speced a local
panel (`python -m agent panel`, `127.0.0.1:5679`, one self-contained HTML
page) for a different job: showing *why* candidates got dropped, via the
per-run JSONL event stream. That panel was never built.

This project stands up the same server and page shell — same command,
same port, same single-file-page constraint — but builds only a
**Reports** view on top of it, backed by the new SQLite store. The
funnel view, the event log, live SSE streaming, and `POST /run` from the
original spec are not built here. They're expected to land later as
additional views/routes on the same server, following that spec.

## Data model

SQLite (stdlib `sqlite3`, no new dependency), at `agent/reports.db`
(gitignored, alongside `agent/state.json` and `agent/runs/`).

```sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL   -- ISO 8601 UTC
);

CREATE TABLE report_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    topic_slug TEXT NOT NULL,
    topic_name TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    score INTEGER NOT NULL,
    summary TEXT NOT NULL,
    published_at TEXT NOT NULL,
    created_at TEXT NOT NULL   -- when this row was stored
);
```

A `runs` row is written on every real run, even when nothing scores
above threshold — that's what lets the dashboard show "ran at 14:00, 0
items" instead of silence. `report_items` holds one row per kept item,
mirroring `digest.build()`'s input (`ranked_by_topic`) instead of
feeding an email body.

## Components

- **`agent/store.py`** (new). Same shape as `agent/dedupe.py`:
  - `init_db(path: Path) -> None` — `CREATE TABLE IF NOT EXISTS` for
    both tables; idempotent, safe to call every time.
  - `save_report(path: Path, run_id: str, now: datetime, ranked_by_topic: dict[str, list[RankedItem]]) -> None`
    — calls `init_db`, inserts one `runs` row and one `report_items` row
    per kept item, commits.
  - `fetch_recent_reports(path: Path, limit: int = 100) -> list[dict]`
    — newest-first, for the panel to read. Returns plain dicts (already
    JSON-serializable) rather than a dataclass, since the only consumer
    is `json.dumps` in the panel's HTTP handler.

- **`agent/main.py`** — `run_real`'s delivery branch changes from:
  ```python
  if total_items:
      deliver.send(subject, body, settings)
      ...
  ```
  to an unconditional call:
  ```python
  store.save_report(REPORTS_DB_PATH, run_id, now, ranked_by_topic)
  for items in ranked_by_topic.values():
      for item in items:
          dedupe.mark_sent(state, item.candidate)
  ```
  `dedupe.mark_sent` still fires per stored item — a stored report is
  what "sent" means now, so the same item doesn't resurface next run.
  `digest.build()` is no longer called from `run_real` (nothing consumes
  its output right now); it stays in the codebase, tested, for whenever
  email comes back.

- **`agent/panel.py`** (new). `http.server.ThreadingHTTPServer` bound
  explicitly to `127.0.0.1:5679` (never a wider bind — see Security
  below). Routes in this pass:
  - `GET /` — serves `agent/panel_page.html` verbatim.
  - `GET /reports` — JSON array from `store.fetch_recent_reports`.

  Not built in this pass (left for the funnel-view follow-up):
  `GET /runs`, `GET /runs/<run_id>`, `GET /events/stream`, `POST /run`.

- **`agent/panel_page.html`** (new). One self-contained file — inline
  CSS, vanilla JS, no framework, no build step, per the run-panel spec's
  existing constraint (deliberately not the same no-JS rule as the
  public static site — this page isn't published). Fetches `/reports`
  on load, renders a list: topic, score, title, one-line summary, link,
  timestamp. No client-side routing needed yet since there's only one
  view.

- **CLI**: `agent/main.py`'s argument parsing gains a `panel` subcommand
  (via `argparse` subparsers) alongside the existing `--dry-run`/
  `--topic` flags. `python -m agent panel` starts the server and blocks;
  Ctrl-C stops it.

- **`agent/run_scheduled.ps1`** (new). Wrapper for Task Scheduler:
  sets the working directory to the repo root explicitly (a scheduled
  task doesn't inherit an interactive shell's cwd), invokes
  `python -m agent` (no `--topic` filter — all three topics in one
  process, one `run_id`), and redirects stdout/stderr to
  `agent/runs/scheduler.log` (Task Scheduler doesn't surface console
  output otherwise).

## Scheduling

Registered via `schtasks /create`, a 4-hour repeating trigger, running
as the current user, pointing at the absolute path to `python.exe`
(resolved once via `(Get-Command python).Source` rather than relying on
PATH resolution inside the scheduled context, which isn't guaranteed to
match an interactive shell's). All three topics run every cycle —
`data-viz` and `full-stack`'s keywords are starting-point values, not
yet tuned, but that's now easy to observe and fix once the dashboard
exists to look at their output in.

`DEEPSEEK_API_KEY` continues to load from `agent/.env` via the existing
`config.load_env` call already in `main()` — no scheduler-specific
secret handling needed.

**Cost**: 3 DeepSeek batch calls per cycle (one per topic), 18/day.
Not tracked further in this spec — cheap enough at this volume per
`agent/defaults.yaml`'s existing model choice.

## Security

The panel binds explicitly to `127.0.0.1`, never a wider address, same
load-bearing constraint the original run-panel spec states — this pass
has no `POST /run` (no unauthenticated subprocess execution), but the
bind address stays a hard requirement regardless, since later work adds
routes to the same server.

## Error handling

- `store.save_report` runs unconditionally (even for a 0-item run) and
  lets DB errors propagate — consistent with `dedupe.mark_sent`'s
  existing philosophy in this codebase: a storage failure is a bug
  worth surfacing loudly, not swallowing.
- `init_db` is idempotent and runs lazily, so the panel doesn't error
  if `reports.db` doesn't exist yet — `fetch_recent_reports` against a
  freshly-initialized empty DB just returns `[]`.
- No special concurrency handling: SQLite's default locking is
  sufficient for one writer (the scheduled run, every 4h) and one
  occasional reader (the panel).
- No retry logic for a failed scheduled run. If DeepSeek or HN Algolia
  is briefly unreachable, that cycle fails, Task Scheduler logs the
  non-zero exit, and the next 4-hour tick runs normally — matches this
  codebase's existing "no automated recovery" pattern.

## Testing / verification

Manual, per this repo's existing convention (no test framework):

- `store.py` — a round-trip script: synthetic `RankedItem`s in,
  `save_report` then `fetch_recent_reports` out, assert fields match;
  confirm a `runs` row exists even when `ranked_by_topic` is empty.
- `run_real` end-to-end — an actual `python -m agent --topic ai-agents`
  run (no `--dry-run`). This is the live-send verification Task 6
  deferred, now redirected to DB instead of SMTP, closing that loop.
  Confirms items land in `reports.db`.
- Panel — start `python -m agent panel`, `curl http://127.0.0.1:5679/reports`
  for the JSON shape, then a visual check of the page in a browser.
- **Bind-address check, carried over from the run-panel spec and still
  the one check that must not be skipped**: confirm the server does not
  answer on the machine's LAN address, only loopback.
- Scheduler — `schtasks /query /tn <name> /v` to confirm the 4-hour
  trigger and next run time; one manual run of `run_scheduled.ps1` to
  confirm it appends to the DB before trusting the schedule to fire on
  its own.

## Out of scope

- The funnel view, event log, live SSE streaming, and `POST /run` from
  the original run-panel spec — expected as a later addition to the
  same server.
- Re-enabling SMTP delivery. `agent/deliver.py` and `agent/digest.py`
  are untouched and still work; nothing in this spec removes them.
- Cost tracking/estimation for the DeepSeek calls.
- Report retention limits or pruning for `reports.db` — revisit if it
  becomes a real size, same open-question posture as `agent/runs/` in
  the original run-panel spec.
