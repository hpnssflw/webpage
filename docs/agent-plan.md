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

- Web search — broad net, catches whatever isn't covered below.
- Hacker News — public Algolia search API, filtered to each topic's keywords.
- A handful of subreddits per topic — chosen once, revisited later if the signal is bad.
- Blog and RSS feeds — a curated list maintained by hand.

## Pipeline

1. **Collect** — each source connector runs independently, returns a flat list of candidate links.
2. **Dedupe** — every link's URL gets hashed against a store of what's already been sent; only new links continue.
3. **Summarize & rank** — an LLM reads each candidate against the three topic descriptions, returns a one-line summary plus a relevance score; anything below the threshold gets dropped.
4. **Assemble** — surviving items get grouped by topic into a digest, ordered by relevance within each group.
5. **Deliver** — the digest goes out by email on a fixed schedule.

## Proposed stack

- A single Python script, run on a schedule rather than a long-lived service.
- `feedparser` for RSS/blog sources; the Hacker News Algolia API and Reddit's public JSON endpoints for the aggregators; a web search API (or Claude's built-in web search) for the broad net.
- A flat JSON file (or SQLite if it outgrows that) holding seen-URL hashes.
- Claude for summarization and relevance scoring.
- A scheduled GitHub Action or plain cron for the trigger; SMTP or a transactional email API (Resend) for delivery.

## Cadence & format

Weekly to start. Each digest groups items under the three topic headers,
five to ten per group, one line of summary and a link each.

## Proposed module layout

Nothing under `agent/` exists yet. First implementation task creates this:

```
agent/
├── main.py              # entry point — runs the full pipeline once
├── config.py             # topic keywords, subreddit list, relevance threshold
├── sources/
│   ├── hn.py              # Hacker News Algolia search
│   ├── reddit.py          # Reddit public JSON endpoints
│   ├── rss.py             # feedparser-based blog/RSS
│   └── web_search.py      # broad web search connector
├── dedupe.py              # seen-URL hash store, backed by seen.json
├── summarize.py           # Claude-based summary + relevance score per candidate
├── digest.py              # groups + orders ranked items into the email body
├── deliver.py             # sends the digest (SMTP or Resend)
├── seen.json              # gitignored — dedupe state, persists between runs
└── requirements.txt
```

## Environment / secrets needed

- `ANTHROPIC_API_KEY` — Claude, for summarization/ranking.
- A search API key, if using one for the broad-web-search connector
  (e.g. Brave Search API) — or Claude's built-in web search if that's
  usable server-side instead.
- SMTP credentials, or `RESEND_API_KEY` if using Resend.
- Destination email address.

`agent/.env` (or equivalent) must be added to `.gitignore` before it's
created — it isn't yet, because nothing reads it yet.

## Task breakdown for the first build session

Smallest useful v1 first — one source end-to-end, not all four at once:

- **TASK-001** — Scaffold `agent/` (the layout above), `requirements.txt`,
  `config.py` with the three topics' keyword lists. Add `agent/seen.json`
  and any `.env` file to `.gitignore`.
- **TASK-002** — Implement `sources/hn.py` (Hacker News Algolia search) —
  smallest source to get working end-to-end first.
- **TASK-003** — Implement `dedupe.py` (JSON seen-URL hash store).
- **TASK-004** — Implement `summarize.py` — one Claude call per candidate,
  returns summary + relevance score; drop below-threshold candidates.
- **TASK-005** — Implement `digest.py` + `deliver.py`, wire `main.py`
  end-to-end using only the HN source. This is v1: collect → dedupe →
  summarize → assemble → email, one working source.
- **TASK-006** — Add the remaining sources (`rss.py`, `reddit.py`,
  `web_search.py`) one at a time, each following the same connector
  interface `hn.py` establishes in TASK-002.
- **TASK-007** — Add scheduling (a scheduled GitHub Action or cron entry).

## Open questions

- Daily vs weekly — start weekly, watch whether Friday's digest already feels stale by Wednesday.
- Resurfacing — a link dismissed once shouldn't come back next week just because dedupe only tracks URLs verbatim.
- Where it runs — a scheduled GitHub Action costs nothing and needs no server, but secrets have to live somewhere (GitHub Actions secrets, most likely).
- Budget — search and LLM calls both cost money per run; weekly cadence keeps this small, but watch it once it's real.

## Status

Planning complete. Implementation not started. Pick up at **TASK-001**.
