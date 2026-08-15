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

### How to resume in a new session

1. Read this file and `docs/superpowers/plans/2026-08-12-research-agent.md`
   (the canonical task list — `docs/agent-plan.md` is background/design
   context, not what to execute against).
2. Add SMTP credentials to `agent/.env` and run
   `python -m agent --topic ai-agents` to finish Task 6's deferred live
   verification (Step 5) — confirm with the user first, since it sends a
   real email. Once that passes, v1 has shipped and there's no Task 7 in
   this plan; TASK-007 onward in `docs/agent-plan.md` (Reddit, RSS,
   releases, web search, attention rescue, scheduling, keyword
   suggestion) is out of scope here and would need its own plan.
3. See `CLAUDE.md` for this repo's actual conventions (no branch/PR flow —
   direct commits to `master`).
