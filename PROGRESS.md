# Project Progress

## Site — Digital Craftsman + LAB + RESEARCHER

**Status: built.**

- Homepage: hero, RESEARCHER topics (with descriptions), LAB feed preview.
- `lab/` — blog listing + one post ("Cheap Models, Strong Graphs", tagged `AI AGENTS`).
- `researcher/` — topics hub page + a single link ("A Research Agent") to the
  agent's plan on `researcher/agent.html`.
- No build step, no JS, no automated tests (plain static HTML/CSS).
- No GitHub remote configured yet — all work is committed directly to `master`.

Design history for the site lives in `docs/superpowers/specs/` and
`docs/superpowers/plans/` (one spec+plan pair per feature, in the order
they were built). `landing-plan.md` at the repo root is the original design
brief this all started from — see the note at its top for what's since
changed.

## Research Agent

**Status: Task 6 of 6 code-complete — one verification step deferred.**

- Narrative plan (public, on the site): `researcher/agent.html`
- Technical plan (background/design, not the task list): `docs/agent-plan.md`
- Canonical implementation plan (the actual step-by-step tasks):
  `docs/superpowers/plans/2026-08-12-research-agent.md` — supersedes the
  coarser TASK-001–007 breakdown at the bottom of `docs/agent-plan.md`.
- `agent/` exists: package scaffold, YAML config (`defaults.yaml` +
  `topics/*.yaml`), the `Candidate`/`Drop`/`TopicConfig` dataclasses
  (`sources/base.py`), and the config loader (`config.py`). Shipped in
  commit `cd77594` — Task 1 of the plan above.
- `agent/date_guard.py` (recency window) and `agent/sources/hn.py` (HN
  Algolia connector) shipped in commit `c4ab1ec` — Task 2. Verified this
  session: synthetic date-guard check passes, and a live Algolia query for
  the `ai-agents` topic returned 32 timezone-aware candidates, 0 drops.
- `agent/dedupe.py` (URL-hash seen-state store, `times_sent`-based
  filtering) shipped in commit `8cc137d` — Task 3. Verified this session:
  a sent item is dropped as `seen` on a later pass, an unsent item is
  kept, and state round-trips through save/load correctly.
- `agent/events.py` (JSONL `EventWriter`), `agent/main.py` (`run_dry`
  funnel), `agent/__main__.py` shipped in commit `7dc7ca1` — Task 4.
  Verified this session: `python -m agent --dry-run --topic ai-agents`
  ran end to end (32 candidates, 0 drops at every stage) and recorded a
  `.jsonl` run file; the event file round-tripped through `read_events`
  with the `collect` stage present; a temporary `max_age_days: 1` edit to
  `ai-agents.yaml` re-ran cleanly with 0 assertion errors (0
  `outside_window` drops, since `hn.collect` already applies
  `max_age_days` server-side via Algolia's `numericFilters`, so
  `date_guard` sees nothing left to catch by the time it runs) and the
  file was restored to its committed form.
- `agent/summarize.py` (batched-per-topic DeepSeek ranking, validated
  against the expected id set, one retry then per-candidate fallback)
  shipped in commit `dd28832` — Task 5. Also updates
  `agent/defaults.yaml`'s `llm.model`: `deepseek-chat` was discontinued
  2026-07-24, so it's now `deepseek-v4-flash` (the non-thinking mode
  `deepseek-chat` used to point to). Verified this session: the
  synthetic response-validator checks all pass with no network, and a
  live batched call against 5 real `ai-agents` candidates returned
  well-formed scores (1–10) and one-sentence summaries for all 5 —
  first paid call in the build. `DEEPSEEK_API_KEY` is set in
  `agent/.env` (gitignored, not committed).
- `agent/digest.py` (subject/body assembly), `agent/deliver.py` (SMTP
  send), and `agent/main.py`'s `run_real` shipped in commit `c65c8cb` —
  Task 6, code side. `docs/agent-plan.md` and `researcher/agent.html`
  synced to the shipped design in commit `5d3605d` (site re-served
  locally and curled to confirm the new copy landed). Verified this
  session: digest assembly (subject line, body content) passes with no
  network. **Deferred:** the plan's Step 5 — one real run
  (`python -m agent --topic ai-agents`) that actually sends mail — is
  not yet done. `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`
  aren't in `agent/.env` yet; a TODO in `agent/deliver.py` marks this.
  Once those credentials are added, run that command and check
  `hypnosisflow@gmail.com` — that's the last thing standing between here
  and "v1 shipped."

### Agent status widget + public dashboard

**Status: in progress — Task 6 of 7 done. The homepage widget is live and rendering real data.**

- Spec: `docs/superpowers/specs/2026-08-15-agent-status-widget-design.md`
  — explicitly supersedes the Windows-Task-Scheduler scheduling decision
  and weekly-cadence-unchanged note in the research-agent spec, and the
  build-time-snapshot public-replay plan in the run-panel spec.
- Plan: `docs/superpowers/plans/2026-08-15-agent-status-widget.md`.
- This repo now has a GitHub remote for the first time:
  `https://github.com/hpnssflw/webpage.git`, local branch renamed
  `master` → `main` to match. The repo is public (required so the site's
  client-side `fetch()` can read `status.json` with no auth token). An
  orphan `agent-data` branch (single commit, `README.md` only) is pushed
  and ready for the GitHub Actions workflow (Task 4) to write to.
  `DEEPSEEK_API_KEY` is set as a repo secret — Task 1, no code changes.
- `.github/workflows/agent-run.yml` (cron `0 */4 * * *` + `workflow_dispatch`,
  two isolated checkouts — `main` read-only into `code/`, `agent-data`
  writable into `data/` — commits/pushes exactly `state.json`,
  `pending.json`, `status.json`) shipped in commit `4c27185`, Task 4. The
  first live run failed with a 403 — the default `GITHUB_TOKEN` is
  read-only unless the workflow requests write access — fixed with a
  scoped `permissions: contents: write` block, commit `c41b696` (an
  overly broad repo-wide permission change was tried first, then
  correctly reverted in favor of this narrower fix). **Both trigger paths
  are now confirmed working against real GitHub infrastructure**: the
  cron schedule fired on its own during testing and pushed successfully,
  and a manual `workflow_dispatch` run right after it pushed again on top
  — `agent-data` now has real commits with a well-formed `status.json`
  (`streak: 2`, real HN titles and DeepSeek relevance scores in
  `recent_events`). Task review independently re-verified the runtime
  token grant (`Contents: write` / `Metadata: read` — confirmed minimal,
  not broader) and reproduced all live-CI claims firsthand; approved, two
  minors deferred (a cp/test terseness nit matching the brief verbatim,
  and the still-open SMTP-not-configured gap from Task 1).
- `agent/pending.py` (pending-email queue), plus rewiring
  `agent/dedupe.py` (`mark_sent` → `mark_sent_url`, called only on actual
  delivery), `agent/digest.py`/`agent/summarize.py` (dropped "weekly"
  wording), `agent/config.py`/`agent/defaults.yaml`
  (`email_cadence_hours: 24`), and `agent/main.py`'s `run_real` — shipped
  in commit `ec64725`, Task 2. This decouples collection/ranking (moving
  to every 4h in Task 4) from email delivery (staying on a 24h rollup),
  and fixes a real bug the spec review caught: without
  `pending.filter_already_pending`, an item sitting in the queue would
  get re-collected and re-sent to DeepSeek for ranking on every
  subsequent cycle until the email gate fires. Verified this session:
  synthetic checks for `is_email_due` (empty/1h/25h against a 24h
  cadence) and `filter_already_pending` (a re-collected duplicate
  correctly dropped) all pass with no network; a live
  `python -m agent --topic ai-agents` run correctly hit the
  SMTP-not-configured graceful-failure path (caught, logged, no
  traceback) rather than crashing, leaving 8 kept items in
  `agent/pending.json` with `last_email_at: null`, ready to send once
  SMTP credentials exist. Task review: spec compliant, no
  Critical/Important findings, approved.
- `agent/status_export.py` (`build_status`, pure — never accepts
  `TopicConfig`, only a `dict[str, str]` of slug→name, so source config
  structurally cannot leak into the public output) shipped in commit
  `905b5e9`, Task 3, wired into `run_real`'s tail to write
  `agent/status.json` after every run (added to `.gitignore` on `main`,
  same as `state.json`/`pending.json` — it's only ever tracked on the
  future `agent-data` branch). Verified this session: a synthetic JSONL
  fixture produces correct funnel counts, `streak` increments on a
  `"run"/"complete"` event and resets to 0 without one, and (added in a
  fix round after task review) a seeded 24-entry `run_history` truncates
  correctly, dropping the oldest and keeping the new entry — all with no
  network; a live run produced a real `status.json` with the expected
  keys and `streak: 1`. Task review: spec compliant; one Important
  plan-mandated finding (the brief's own test script didn't cover the
  24-entry cap) fixed in a follow-up round; three Minor items deferred
  (worth noting for Task 4: a genuinely crashed run never reaches
  `build_status` at all, so `streak` only ever resets via the code path,
  not via an actual production failure — a crashed run just leaves the
  public widget's last-known state stale rather than flipping it red;
  the stale-dot logic in Task 5/6/7 is what actually catches that case).
- `assets/agent-widget.js` (shared vanilla-JS fetch/render script — fetch
  on load only, no polling; renders into `#agent-widget` and/or
  `#agent-dashboard`, whichever exists; `STATUS_URL` points at
  `raw.githubusercontent.com/hpnssflw/webpage/agent-data/agent/status.json`)
  shipped in commit `226406f`, Task 5. All status.json-derived string
  content (title, topic, reason, topic name) is HTML-escaped before
  interpolation. Verified this session via jsdom driving the actually-
  served page (no real browser tool available in this environment) —
  confirmed dot-class toggling on fresh vs. stale `updated_at`, sparkline
  rendering, countdown math, and per-topic counts; literal color
  rendering is correctly deferred to Task 6, since the CSS classes don't
  exist yet. Task review: spec compliant, approved, three minors
  deferred (notably: the dashboard's countdown call is currently a
  harmless no-op — the dashboard mockup never included a countdown
  element by design, so there's no `[data-countdown]` target for it to
  find).
- Homepage widget markup (`#agent-widget` mount under the RESEARCHER
  topics list, `assets/agent-widget.js` script tag) and its CSS (card
  chrome on `.agent-widget-link`, not a bare `.agent-widget` class —
  there is no such class in the DOM, only the `#agent-widget` id; the
  `.accent` comment updated to acknowledge this as the second deliberate
  monochrome-palette break) shipped in commit `02797dc`, Task 6.
  **Confirmed rendering real production data** — verified this session
  against the actual live `agent-data` `status.json` (streak 2, sparkline
  `█▃`, real per-topic counts), not just the fallback state. Task review
  independently re-fetched the same live JSON and confirmed the reported
  figures weren't fabricated; approved, two minors deferred (both in the
  plan's own text, not implementation: a self-contradictory CSS comment,
  and an intentionally-unstyled `.agent-topics` span).
- Note: there is unrelated concurrent work on `main` from a different
  session implementing the local run panel
  (`docs/superpowers/specs/2026-08-12-run-panel-design.md`) —
  `agent/panel.py`, `agent/funnel.py`, `agent/panel_page.html`, and edits
  to `agent/main.py` (a `panel` subcommand, and — as of this writing, seen
  mid-edit — refactoring `run_dry` into `run_dry_pipeline` for a live-
  trigger feature). No conflict with this plan's tasks so far; flagging
  so a future session isn't surprised by commits it didn't make.

### How to resume in a new session

**Research agent v1 (original 6-task plan):**

1. Read `docs/superpowers/plans/2026-08-12-research-agent.md` (the
   canonical task list — `docs/agent-plan.md` is background/design
   context, not what to execute against).
2. Add SMTP credentials to `agent/.env` and run
   `python -m agent --topic ai-agents` to finish Task 6's deferred live
   verification (Step 5) — confirm with the user first, since it sends a
   real email. Once that passes, v1 has shipped and there's no Task 7 in
   this plan; TASK-007 onward in `docs/agent-plan.md` (Reddit, RSS,
   releases, web search, attention rescue, scheduling, keyword
   suggestion) is out of scope here and would need its own plan.

**Agent status widget (new 7-task plan, in progress):**

1. Read `docs/superpowers/plans/2026-08-15-agent-status-widget.md` and
   this file's section above.
2. Confirm the next task (**Task 7 — dashboard section on
   researcher/agent.html + narrative sync**, the final task) with the
   user before writing any code.
3. This plan is being executed via
   `superpowers:subagent-driven-development`; its ledger is at
   `.superpowers/sdd/2026-08-15-agent-status-widget/progress.md`
   (git-ignored) if a session needs to recover mid-plan.

**General:** see `CLAUDE.md` for this repo's actual conventions. Note the
GitHub remote and `main` branch (above) are new as of the widget plan —
`CLAUDE.md`'s "no GitHub remote configured... direct commits to `master`"
line describes the state before that plan; commits still go directly to
`main` with no PR flow, just under a new branch name and with a remote
now attached.
