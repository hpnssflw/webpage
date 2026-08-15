# Research Agent — Technical Plan

This is the **canonical, implementation-facing** version of the plan. The
public-facing narrative version lives at `researcher/agent.html` on the
site — keep the two in sync at a high level (goal, sources, pipeline,
stack) whenever this changes materially; they don't need to match
word-for-word.

## Goal

A background agent that reads so Artem doesn't have to read everything
himself. Once a week it produces a short, curated list of what actually
moved in three topics — links and a one-line summary each. Nothing
published, nothing public. Raw material for his own LAB writing, not a
LAB post itself.

## Topics (fixed set, matches the site's RESEARCHER section)

- **Data Viz** — BI dashboards, browser graphics, render-engine performance.
- **Full-Stack Architecture** — trends, architectures, best practices and
  patterns across the modern web stack.
- **AI Agents & Engineering** — trends, architectures and patterns for
  building and running agents in production.

## Sources

- Hacker News — public Algolia search API, filtered to each topic's keywords.
- Blog and RSS feeds — a curated list maintained by hand, one per topic.
- Repo release watching — GitHub releases API for a handful of watched repos per topic; a version bump is unambiguous news.
- A handful of subreddits per topic — chosen once, revisited later if the signal is bad.
- Web search — broad net via a dedicated search API with a freshness filter (not Claude's built-in web search, which has no date parameter), catches whatever isn't covered above.

Every source returns a publish date for each candidate; undated candidates
are dropped rather than passed through. Full detail:
`docs/superpowers/specs/2026-08-12-research-agent-design.md`.

## Pipeline

1. **Collect** — each source connector runs independently, returns candidate links with a mandatory publish date.
2. **Recency window** — candidates published outside the topic's `max_age_days` are dropped; an item whose score has since jumped can re-enter (the attention window).
3. **Dedupe** — every link's URL gets hashed against a store of what's already been sent; only new links continue.
4. **Rank** — one batched LLM call per topic ranks all of that topic's surviving candidates against each other and against the topic description, returning a one-line summary and a relevance score per item; anything below the threshold, or beyond the per-topic item cap, gets dropped.
5. **Assemble** — surviving items get grouped by topic into a digest, ordered by relevance within each group.
6. **Deliver** — the digest goes out by email on a fixed schedule.

Every stage emits a structured event to a per-run log, so a run is
inspectable after the fact — see the run panel plan,
`docs/superpowers/specs/2026-08-12-run-panel-design.md`.

## Proposed stack

- A single Python script, run on a schedule rather than a long-lived service.
- `feedparser` for RSS/blog sources; the Hacker News Algolia API, Reddit's public JSON endpoints, and the GitHub releases API for the other aggregators; a dedicated search API (Brave) for the broad net, chosen because it returns a publish date per result.
- A flat JSON file (or SQLite if it outgrows that) holding seen-URL hashes and score history.
- DeepSeek for summarization and relevance scoring, via the OpenAI-compatible `openai` SDK — cheap enough at this volume that ranking quality, not price, is the thing to tune.
- Windows Task Scheduler for the trigger (this repo has no GitHub remote); SMTP for delivery.

## Cadence & format

Weekly to start. Each digest groups items under the three topic headers,
five to ten per group, one line of summary and a link each.

## Proposed module layout

See `docs/superpowers/specs/2026-08-12-research-agent-design.md` for the
current module layout, YAML control surface, and candidate/event
contracts — this section is superseded there.

## Environment / secrets needed

- `DEEPSEEK_API_KEY` — DeepSeek, for summarization/ranking.
- `BRAVE_API_KEY` — the web search connector.
- `GITHUB_TOKEN` — optional; raises the release-watching connector's rate limit.
- SMTP host, port, user, password — delivery.

`agent/.env` is gitignored.

## Task breakdown for the first build session

Superseded by the build order in
`docs/superpowers/specs/2026-08-12-research-agent-design.md`. As of this
writing, TASK-001 through TASK-006 are complete — the agent runs
end-to-end on Hacker News only, ranked by DeepSeek and delivered by email.
Reddit, RSS, release watching, web search, the attention window,
scheduling, and self-refreshing keywords remain.

## Open questions

- Daily vs weekly — start weekly, watch whether Friday's digest already feels stale by Wednesday.
- Resurfacing — a link dismissed once shouldn't come back next week just because dedupe only tracks URLs verbatim.
- Where it runs — resolved: Windows Task Scheduler (this repo has no GitHub remote), secrets in `agent/.env`.
- Budget — search and LLM calls both cost money per run; weekly cadence keeps this small, but watch it once it's real.

## Status

v1 code-complete: collect (Hacker News) → recency window → dedupe → rank
(DeepSeek) → assemble → deliver (SMTP), running by hand. The SMTP send
path is implemented but not yet exercised against a real inbox — SMTP
credentials aren't in `agent/.env` yet (see the TODO in
`agent/deliver.py`). Remaining sources, scheduling, and the attention
window are tracked in
`docs/superpowers/specs/2026-08-12-research-agent-design.md`.
