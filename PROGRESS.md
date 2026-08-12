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

**Status: planned, not started.**

- Narrative plan (public, on the site): `researcher/agent.html`
- Technical plan (canonical for implementation): `docs/agent-plan.md`
- Nothing under `agent/` exists yet — that directory doesn't exist in the
  repo. The first implementation task creates it.

### How to resume in a new session

1. Read this file and `docs/agent-plan.md`.
2. Confirm the next task (starts at **TASK-001**, see `docs/agent-plan.md`)
   with the user before writing any code.
3. See `CLAUDE.md` for this repo's actual conventions (no branch/PR flow —
   direct commits to `master`).
