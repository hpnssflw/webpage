# Research agent — control surface, freshness, and event stream

## Purpose

Build the research agent described in `docs/agent-plan.md`, with three
changes to that plan driven by two requirements the original didn't cover:
comfortable day-to-day control over topics and sources, and a guarantee that
what lands in the digest is actually recent.

The three changes:

1. Topics and sources move out of `config.py` into hand-editable YAML files.
2. Every source connector must return a publish date, and undated candidates
   are dropped rather than passed through.
3. Every pipeline stage emits a structured event, so a run is inspectable
   after the fact and watchable while it happens.

Change 3 exists to serve the run panel (see
`2026-08-12-run-panel-design.md`), but it belongs to the agent — the panel is
one renderer over a stream the agent produces regardless.

This spec supersedes the "Proposed module layout", "Sources", "Pipeline", and
"Task breakdown" sections of `docs/agent-plan.md`. The Goal, Topics, and
Cadence sections of that document still stand.

## Control surface

Configuration lives in `agent/defaults.yaml` plus one file per topic under
`agent/topics/`. Both are git-tracked. Adding a topic means copying a file;
retiring one means deleting it; muting a source means deleting its key.

```yaml
# agent/defaults.yaml — applies to every topic unless overridden
max_age_days:   10
min_relevance:  6      # 1–10 scale
max_items:      8
attention:
  enabled:         true
  min_score_gain:  50

llm:
  base_url: https://api.deepseek.com
  model:    deepseek-chat

delivery:
  to:   hypnosisflow@gmail.com
  from: agent@localhost
```

```yaml
# agent/topics/ai-agents.yaml
name: AI Agents & Engineering
description: >
  Trends, architectures and patterns for building and
  running agents in production.
keywords: [agent framework, tool use, evals, MCP]

sources:
  hacker_news: { min_points: 30 }
  reddit:      [LocalLLaMA, AI_Agents]
  rss:         [https://simonwillison.net/atom/everything/]
  releases:    [anthropics/claude-code, modelcontextprotocol/servers]
  web_search:
    queries: ["production AI agent architecture"]
```

`config.py` loads `defaults.yaml`, then each topic file, and merges the two
per topic. A topic file states only what differs from the defaults. Any
top-level default key may be overridden in a topic file; `sources` has no
default and must be stated per topic.

Three topic files ship initially, matching the site's RESEARCHER section:
`data-viz.yaml`, `full-stack.yaml`, `ai-agents.yaml`.

## The candidate contract

Every connector returns the same shape, and `published_at` is mandatory:

```python
@dataclass(frozen=True)
class Candidate:
    url:          str
    title:        str
    source:       str            # hn | reddit | rss | releases | web
    topic:        str            # topic slug
    published_at: datetime       # timezone-aware UTC
    score:        int | None     # HN points, Reddit ups; None where absent
    excerpt:      str | None
```

The connector interface is one function per module:

```python
def collect(topic: TopicConfig, now: datetime) -> Iterable[Candidate]: ...
```

A required `published_at` is what makes the recency window enforceable in one
place instead of five. A connector that cannot determine a date for an item
does not invent one and does not emit the candidate — it emits a drop event
with reason `undated`.

**Undated items fail closed.** This is deliberate: a silently undated item is
exactly how stale content reaches a digest that claims to be current, and
there is no way to notice it after the fact.

### Date sources per connector

| Connector  | Endpoint                                      | Date field     | Native filter |
|------------|-----------------------------------------------|----------------|---------------|
| `hn`       | Algolia `/api/v1/search`                      | `created_at_i` | `numericFilters=created_at_i>N,points>M` |
| `reddit`   | `reddit.com/r/<sub>/top.json?t=week`          | `created_utc`  | `t=week` |
| `rss`      | `feedparser`                                  | `published_parsed`, else `updated_parsed` | none — filtered client-side |
| `releases` | GitHub `/repos/<owner>/<repo>/releases`       | `published_at` | none — filtered client-side |
| `web`      | Brave Search API                              | `page_age`     | `freshness` parameter |

Reddit requires an explicit `User-Agent` header or it returns 429. GitHub's
unauthenticated rate limit is low enough to matter across several repos —
`releases.py` reads an optional `GITHUB_TOKEN` and works without it.

**Brave is the chosen search provider** because it has a `freshness` request
parameter and returns `page_age` on results, which is the minimum needed to
satisfy the recency window server-side. Tavily and Exa both qualify too;
Brave is the default because its free tier suits this volume. Its current
quota is to be confirmed against Brave's documentation at TASK-008 before the
connector is written — if it no longer fits, swapping providers is one module
behind the same `collect()` interface.

## Freshness mechanisms

Four mechanisms, all resting on the candidate contract.

**Hard recency window.** Filtered twice: server-side via each API's native
filter where one exists, and again in the pipeline against
`topic.max_age_days`. The native filter saves bandwidth; the pipeline guard
is what guarantees the invariant, including for connectors with no native
filter.

**Attention window.** An item outside the window still enters if its score
rose by at least `attention.min_score_gain` since the last run. Applies only
to sources that report a score (`hn`, `reddit`).

This requires score history, so the state store is loaded **before** the date
guard runs, not as part of the dedupe stage — the guard consults
`last_score` to decide whether to rescue. An item that survives by rescue is
marked as such and is exempt from the `seen` check downstream; without that
exemption the rescue would be undone one stage later and the mechanism would
be dead code.

**Release watching.** `releases.py` is a first-class connector, not a special
case of RSS. GitHub returns `published_at` directly, making it the cleanest
date contract of the five.

**Self-refreshing queries.** A separate command, not part of the weekly run:

```
python -m agent suggest-keywords
```

It reads recent run records, asks the model what terminology appears in
high-scoring items that the topic's `keywords` list does not cover, and
appends a commented block to the topic YAML:

```yaml
# suggested 2026-08-12: context compaction, subagent orchestration
```

It never edits the live `keywords` list. An agent that silently rewrites its
own search criteria is one bad suggestion away from drifting off-topic with
no signal that this is what happened — the digest would just quietly get
worse.

## State

`agent/state.json`, gitignored, keyed by URL hash:

```json
{
  "a3f1…": { "first_seen": "2026-08-05T09:00:00Z", "last_score": 142, "times_sent": 1 }
}
```

**The store records every candidate seen, but dedupe drops only those with
`times_sent > 0`.** An item that was collected and then dropped — below
threshold, outside the window, under `min_points` — is recorded so its score
history accumulates, and may legitimately return on a later run once it has
gained traction. Only an item that actually reached the inbox is a duplicate.

`last_score` powers the attention window and is updated on every run,
including for candidates that get dropped. `times_sent` is what dedupe reads,
and is also the data a future resurfacing rule would need (an open question
in `docs/agent-plan.md`); no such rule exists in this build.

SQLite if this outgrows a flat file, but it will not at this volume.

## Pipeline

```
collect → date-guard → dedupe → rank → assemble → deliver
             ↑                    ↑
        drops undated       first paid call
```

Both filters run before the model, so token spend scales with new recent
items rather than everything collected. A quiet week costs almost nothing.

## Ranking

`summarize.py` calls the DeepSeek API through the `openai` SDK with
`base_url` pointed at `llm.base_url`. DeepSeek's API is OpenAI-compatible, so
changing provider is a config change and needs no abstraction layer.

**Ranking is batched per topic, not per candidate.** One call receives a
topic's whole candidate set and returns a ranked list. This differs from
`docs/agent-plan.md`, which specified one call per candidate.

The reason is calibration. Independent per-item scoring gives the model no
reference point, so a 7 in a quiet week and a 7 in a busy week do not mean
the same thing and `min_relevance` silently drifts. Comparative ranking
within a batch produces stable relative ordering, which is what "the top
eight this week" actually requires.

Request: topic name, topic description, and a numbered list of candidates
(title, source, excerpt). Response: a JSON array of
`{id, summary, score}` where `summary` is one line and `score` is 1–10.

**DeepSeek's JSON mode is a request, not a schema guarantee**, so the
response is validated rather than trusted: every sent id present, no
unexpected ids, `score` an integer in range. On failure, retry once; on a
second failure, fall back to per-item calls for that topic so a malformed
batch costs one topic's ordering rather than its entire section.

Batches stay within one topic (~25 items) to bound that blast radius.

Model IDs and JSON-mode behaviour are to be confirmed against DeepSeek's
current documentation at TASK-005; `deepseek-chat` is the starting value.

## Event stream

Every stage appends to `agent/runs/<run_id>.jsonl`, where `run_id` is a UTC
timestamp (`2026-08-12T0900Z`). `events.py` owns the emitter.

```jsonl
{"ts":"…","stage":"collect","source":"hn","topic":"ai-agents","event":"candidate","url":"…","title":"…"}
{"ts":"…","stage":"date_guard","event":"drop","url":"…","reason":"outside_window","detail":{"published_at":"2026-06-02","max_age_days":10}}
{"ts":"…","stage":"rank","event":"drop","url":"…","reason":"below_relevance","detail":{"score":4,"min_relevance":6}}
{"ts":"…","stage":"deliver","event":"sent","detail":{"items":24,"topics":3}}
```

**A drop event carries a machine-readable reason and the values that caused
it.** This is the difference between a debugging tool and a log viewer:
"why is the digest empty this week" becomes one glance rather than an
investigation.

Drop reasons are a closed set — `undated`, `outside_window`,
`below_min_points`, `seen`, `below_relevance`, `over_max_items` — and each
carries both the threshold and the actual value in `detail`.

`--dry-run` runs collect through rank-input and emits the same events, then
stops before the first model call and sends nothing. Terminal output is a
renderer over the stream, not a separate code path.

## Module layout

```
agent/
├── main.py            # entry point; --dry-run, --topic, subcommands
├── config.py          # merges defaults.yaml + topics/*.yaml
├── events.py          # JSONL emitter
├── defaults.yaml
├── topics/
│   ├── data-viz.yaml
│   ├── full-stack.yaml
│   └── ai-agents.yaml
├── sources/
│   ├── base.py        # Candidate, TopicConfig, collect() protocol
│   ├── hn.py
│   ├── reddit.py
│   ├── rss.py
│   ├── releases.py
│   └── web_search.py
├── dedupe.py          # state.json read/write, attention window
├── summarize.py       # DeepSeek batched ranking
├── digest.py          # group + order into the email body
├── deliver.py         # SMTP
├── state.json         # gitignored
├── runs/              # gitignored
└── requirements.txt   # pyyaml, feedparser, openai, requests
```

Delivery is SMTP rather than Resend: it needs no third-party account and one
fewer key, and `deliver.py` is small enough to swap later if SMTP proves
irritating.

## Environment and secrets

- `DEEPSEEK_API_KEY` — ranking.
- `BRAVE_API_KEY` — web search connector (TASK-008 onward).
- `GITHUB_TOKEN` — optional; raises the releases connector's rate limit.
- SMTP host, port, user, password.

Read from `agent/.env`. **`agent/.env`, `agent/state.json`, and `agent/runs/`
must be added to `.gitignore` in TASK-001, before any of them exist.**

## Build order

| Task | Work | Rationale |
|------|------|-----------|
| 001 | Scaffold `agent/`, `defaults.yaml`, three topic files, `config.py`, `sources/base.py`, gitignore entries | |
| 002 | `sources/hn.py` + the date guard | Smallest connector; proves the candidate contract |
| 003 | `dedupe.py` + `state.json` | |
| 004 | `events.py` + `--dry-run` end to end with a terminal renderer | Costs nothing to run, makes every later config decision checkable rather than guessed |
| 005 | `summarize.py` — batched, validated, per-item fallback | First paid call |
| 006 | `digest.py` + `deliver.py`, `main.py` wired end to end | **v1 ships** — HN only |
| 007 | `sources/rss.py`, `sources/releases.py` | Releases before Reddit: cleanest date contract, highest signal |
| 008 | `sources/reddit.py`, `sources/web_search.py` | Confirm Brave's quota first |
| 009 | Attention window | Needs score history from 003 to have accumulated |
| 010 | Scheduling | |
| 011 | `suggest-keywords` | Needs run-record history to learn from |

TASK-004 is moved ahead of the model integration relative to
`docs/agent-plan.md`. The dry run is what makes the YAML control surface
tunable, and it is testable at zero cost.

**Scheduling is Windows Task Scheduler, not a GitHub Action.** This repo has
no GitHub remote configured (`CLAUDE.md`), and the machine is Windows.
`docs/agent-plan.md` assumes a scheduled GitHub Action; that assumption does
not hold and the plan document needs correcting.

## Documentation to keep in sync

Per `CLAUDE.md`, `researcher/agent.html` and `docs/agent-plan.md` describe the
same agent at two levels of detail and must stay aligned at a high level.
Both need updating as part of this work:

- Sources grows from four to five (releases added).
- The freshness contract is new in both.
- `docs/agent-plan.md`'s LLM is Claude; it is now DeepSeek.
- `docs/agent-plan.md`'s scheduling assumption (GitHub Action) is wrong.

Update them at TASK-006, when v1 ships and the design has survived contact
with a working pipeline — not before.

## Out of scope

- The run panel — see `2026-08-12-run-panel-design.md`. This spec produces
  the event stream it consumes and nothing more.
- Resurfacing rules beyond URL-verbatim dedupe. `times_sent` is recorded so a
  future rule has data; no rule reads it here.
- Publishing anything. The digest is private email; nothing reaches the site.
- Changing the three topics or the weekly cadence.

## Testing / verification

This repo has no automated test suite and the agent adds no framework for
one. Verification is per-task and manual:

- **TASK-002 onward** — each connector is verified by running `--dry-run`
  against a single topic and confirming candidate counts are non-zero and
  every emitted candidate carries a `published_at` inside the window.
- **The date guard specifically** — verified by temporarily setting
  `max_age_days: 1` on one topic and confirming the drop count rises and
  every drop event carries `reason: outside_window` with both values in
  `detail`.
- **TASK-005** — the ranking validator is verified by feeding it a
  deliberately malformed response and confirming it retries, then falls back
  to per-item calls rather than raising or dropping the topic silently.
- **TASK-006** — one full run to a real inbox, checked by eye.
- No network calls in any verification step run against a paid endpoint until
  TASK-005; everything before it is free.

## Open questions

- Whether SMTP stays, or Resend earns its extra key. Revisit after the first
  few real deliveries.
- Whether weekly holds. Unchanged from `docs/agent-plan.md` — watch whether
  Friday's digest feels stale by Wednesday.
- Whether `min_relevance: 6` is the right default. It is a guess until a few
  runs of real ranked output exist to calibrate against; the dry run and the
  run records are what make recalibrating cheap.
