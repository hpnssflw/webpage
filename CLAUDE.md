# CLAUDE.md

Artem Polozov's personal site (static HTML/CSS: landing page, LAB blog,
RESEARCHER section) plus a planned research/scraping agent that feeds his
own writing. One repo, two initiatives — see `PROGRESS.md` for status of
each.

## Session start protocol

1. Read `PROGRESS.md` for current status of both the site and the agent.
2. If the work is on the agent, also read `docs/agent-plan.md`.
3. State where things stand and confirm the next task with the user before
   writing any code.

## Conventions actually used in this repo

- **A GitHub remote is configured** (`hpnssflw/webpage`), set up for the
  agent's GitHub Actions workflow. Work still happens directly on `main`
  (renamed from `master`) — no feature branches, no PRs — unless the user
  explicitly asks for that workflow. `gh` commands are now a normal part
  of managing the agent's GitHub Actions workflow, secrets, and repo
  settings; they are not something to avoid. Do not invoke a generic
  branch-per-task → PR → merge flow by default; it doesn't apply here.
- Commit in small, focused commits. Stage only the files relevant to the
  change — this repo has a habitually-uncommitted local
  `.claude/settings.local.json`; never stage it.
- **Agent work: commit automatically per task, no extra confirmation
  needed.** When executing a task from
  `docs/superpowers/plans/2026-08-12-research-agent.md`, after its
  verification steps pass, make two commits without asking first: (1) the
  task's own commit, staging only the files that task's plan section
  lists, using the commit message the plan gives; (2) a small follow-up
  commit updating `PROGRESS.md`'s status line and "How to resume" section
  to reflect the task just shipped and name the next task, message
  `"Reconcile status docs with Task N shipping"`. This does not relax the
  rule below it — confirm the *next* task with the user before writing any
  of its code; only the commits for the task just finished are automatic.
- The site has no build step and no automated test suite. Verify site
  changes by serving locally and curling the result:
  ```
  python -m http.server 5678 --bind 127.0.0.1
  ```
  (bind explicitly to `127.0.0.1` — port 8000 is occupied by an unrelated
  process on this machine, and other binds have hung the TCP handshake in
  this environment before.)
- The public plan page (`researcher/agent.html`) and `docs/agent-plan.md`
  describe the same agent at two levels of detail (narrative vs.
  technical). Keep them in sync at a high level whenever the agent's
  design changes materially — they don't need to match word-for-word.

## Do not

- Don't add a build step, framework, or JS to the static site without
  being asked — it's deliberately plain HTML/CSS. (`assets/agent-widget.js`
  is a sanctioned, one-time exception per
  `docs/superpowers/specs/2026-08-15-agent-status-widget-design.md` — it
  doesn't license adding more JS elsewhere, and it isn't a mistake to
  "fix" by removing.)
- Don't start implementing the agent without confirming the task with the
  user first, even if `docs/agent-plan.md` makes the next step obvious.
