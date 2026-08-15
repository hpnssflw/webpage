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

**Status: in progress — Task 3 of 6 done.**

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

### How to resume in a new session

1. Read this file and `docs/superpowers/plans/2026-08-12-research-agent.md`
   (the canonical task list — `docs/agent-plan.md` is background/design
   context, not what to execute against).
2. Confirm the next task (**Task 4 — Event stream + dry run**) with the
   user before writing any code.
3. See `CLAUDE.md` for this repo's actual conventions (no branch/PR flow —
   direct commits to `master`).
