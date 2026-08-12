# Research Agent (v1: TASK-001–006) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the research agent through v1 — a Python pipeline that
collects Hacker News candidates for three topics, filters them for recency,
dedupes against prior runs, ranks them with DeepSeek, and emails a digest —
plus the YAML control surface and JSONL event stream that make it tunable
and inspectable.

**Architecture:** A small package (`agent/`) of single-responsibility
modules connected by two plain dataclasses (`Candidate`, `Drop`). Config
lives in YAML, never in Python. Every pipeline stage returns
`(kept, dropped)` rather than mutating shared state, and a thin
orchestration layer in `main.py` threads those tuples through the stages
and into an event log. TASK-001 through TASK-006 cover scaffold through
"v1 ships" (HN only); TASK-007 onward (Reddit, RSS, releases, web search,
attention rescue, scheduling, keyword suggestion) are out of scope for this
plan.

**Tech Stack:** Python 3.12, stdlib + `pyyaml`, `requests`, `openai` (used
against DeepSeek's OpenAI-compatible endpoint). No test framework, no build
step, no venv — this environment's global interpreter already has
`pyyaml`, `requests`, and `openai` installed.

## Global Constraints

- **`Candidate.published_at` is mandatory and always timezone-aware UTC.**
  A connector that cannot determine a date for an item never constructs a
  `Candidate` for it — it returns a `Drop` with `reason="undated"` instead.
  (Spec § The candidate contract.)
- **Drop reasons are a closed set:** `undated`, `outside_window`,
  `below_min_points`, `seen`, `below_relevance`, `over_max_items`. Every
  `Drop` carries both the threshold and the actual value in `detail`.
  (Spec § Event stream.)
- **Config lives in `agent/defaults.yaml` + `agent/topics/*.yaml`.** Never
  hardcode topic names, keywords, or thresholds in Python. (Spec § Control
  surface.)
- **Ranking is batched per topic** (one call for the whole topic's
  candidate set, not one call per candidate), validated against the
  expected id set before use, retried once on validation failure, then
  falls back to per-candidate calls for that topic only. (Spec § Ranking.)
- **No network call against a paid endpoint (DeepSeek) until TASK-005.**
  Everything before it is free (HN Algolia has no auth, SMTP is only
  exercised in TASK-006). (Spec § Testing / verification.)
- **Delivery is SMTP**, read from environment variables, not a
  transactional email API. (Spec § Module layout.)
- **`agent/.env`, `agent/state.json`, `agent/runs/` are gitignored** and
  must never be staged. (Spec § Environment and secrets.)
- **No automated test framework.** This repo has none and the agent adds
  none — every task's verification step is a manual command run and a
  read of its output, per the spec's own Testing / verification section.
- **Commit only files relevant to each task.** Never stage
  `.claude/settings.local.json` (repo convention, `CLAUDE.md`).

---

## Task 1: Scaffold — package, config loader, candidate contract

**Files:**
- Create: `agent/__init__.py`
- Create: `agent/defaults.yaml`
- Create: `agent/topics/ai-agents.yaml`
- Create: `agent/topics/data-viz.yaml`
- Create: `agent/topics/full-stack.yaml`
- Create: `agent/sources/__init__.py`
- Create: `agent/sources/base.py`
- Create: `agent/config.py`
- Create: `agent/requirements.txt`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing (first task)
- Produces:
  - `agent.sources.base.Candidate` — frozen dataclass: `url: str`,
    `title: str`, `source: str`, `topic: str`,
    `published_at: datetime`, `score: int | None`, `excerpt: str | None`
  - `agent.sources.base.Drop` — frozen dataclass: `url: str`,
    `title: str`, `reason: str`, `detail: dict`
  - `agent.sources.base.TopicConfig` — frozen dataclass: `slug: str`,
    `name: str`, `description: str`, `keywords: list[str]`,
    `sources: dict`, `max_age_days: int`, `min_relevance: int`,
    `max_items: int`, `attention_enabled: bool`,
    `attention_min_score_gain: int`
  - `agent.config.LLMConfig` — frozen dataclass: `base_url: str`, `model: str`
  - `agent.config.DeliveryConfig` — frozen dataclass: `to: str`, `from_: str`
  - `agent.config.Settings` — frozen dataclass: `llm: LLMConfig`,
    `delivery: DeliveryConfig`
  - `agent.config.load_settings(defaults_path: Path) -> Settings`
  - `agent.config.load_topics(topics_dir: Path, defaults_path: Path) -> list[TopicConfig]`
  - `agent.config.load_env(path: Path) -> None`

- [ ] **Step 1: Create the package init**

`agent/__init__.py`:

```python
```

(Empty — marks `agent/` as a package.)

- [ ] **Step 2: Create `agent/sources/__init__.py`**

```python
```

(Empty — marks `agent/sources/` as a package.)

- [ ] **Step 3: Write `agent/sources/base.py`**

```python
"""Shared types every source connector and pipeline stage depends on."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Candidate:
    """One item a source connector found. published_at is mandatory —
    a connector that cannot determine a date drops the item instead of
    inventing one."""

    url: str
    title: str
    source: str  # hn | reddit | rss | releases | web
    topic: str  # topic slug
    published_at: datetime  # timezone-aware UTC
    score: int | None  # HN points, Reddit ups; None where the source has no score
    excerpt: str | None


@dataclass(frozen=True)
class Drop:
    """A candidate (or would-be candidate) that a pipeline stage rejected,
    with enough detail to answer "why" without reading code."""

    url: str
    title: str
    reason: str  # undated | outside_window | below_min_points | seen | below_relevance | over_max_items
    detail: dict


@dataclass(frozen=True)
class TopicConfig:
    """One topic's fully merged configuration — defaults.yaml with this
    topic's overrides from topics/<slug>.yaml applied on top."""

    slug: str
    name: str
    description: str
    keywords: list[str]
    sources: dict
    max_age_days: int
    min_relevance: int
    max_items: int
    attention_enabled: bool
    attention_min_score_gain: int
```

- [ ] **Step 4: Write `agent/defaults.yaml`**

```yaml
# Applies to every topic unless overridden in that topic's own file.
max_age_days: 10
min_relevance: 6 # 1-10 scale
max_items: 8
attention:
  enabled: true
  min_score_gain: 50

llm:
  base_url: https://api.deepseek.com
  model: deepseek-chat

delivery:
  to: hypnosisflow@gmail.com
  from: agent@localhost
```

- [ ] **Step 5: Write the three topic files**

`agent/topics/ai-agents.yaml` (exact content from the spec):

```yaml
name: AI Agents & Engineering
description: >
  Trends, architectures and patterns for building and
  running agents in production.
keywords: [agent framework, tool use, evals, MCP]

sources:
  hacker_news: { min_points: 30 }
  reddit: [LocalLLaMA, AI_Agents]
  rss: [https://simonwillison.net/atom/everything/]
  releases: [anthropics/claude-code, modelcontextprotocol/servers]
  web_search:
    queries: ["production AI agent architecture"]
```

`agent/topics/data-viz.yaml`:

```yaml
name: Data Viz
description: >
  BI dashboards, browser graphics, and render-engine performance.
keywords:
  [data visualization, dashboard, WebGL, canvas rendering, charting library]

sources:
  hacker_news: { min_points: 20 }
  reddit: [dataisbeautiful, visualization]
  rss: [https://blog.datawrapper.de/feed/]
  releases: [d3/d3, apache/echarts, observablehq/plot]
```

`agent/topics/full-stack.yaml`:

```yaml
name: Full-Stack Architecture
description: >
  Trends, architectures, best practices and patterns across the
  modern web stack.
keywords:
  [full-stack architecture, server components, edge deployment, web framework]

sources:
  hacker_news: { min_points: 30 }
  reddit: [webdev, programming]
  rss: [https://overreacted.io/rss.xml]
  releases: [vercel/next.js, sveltejs/svelte]
```

These three files' `sources` and `keywords` are starting points, not
researched final values — they exist so the pipeline has something real to
run against from TASK-002 onward. The dry run built in TASK-004 is what
makes tuning them cheap; expect to revise all three once it exists.

- [ ] **Step 6: Write `agent/config.py`**

```python
"""Load and merge agent configuration: defaults.yaml + one file per topic."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from agent.sources.base import TopicConfig


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str


@dataclass(frozen=True)
class DeliveryConfig:
    to: str
    from_: str


@dataclass(frozen=True)
class Settings:
    llm: LLMConfig
    delivery: DeliveryConfig


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override on top of base; override wins on
    conflicting scalar keys, dicts are merged key by key."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_settings(defaults_path: Path) -> Settings:
    raw = _load_yaml(defaults_path)
    llm_raw = raw["llm"]
    delivery_raw = raw["delivery"]
    return Settings(
        llm=LLMConfig(base_url=llm_raw["base_url"], model=llm_raw["model"]),
        delivery=DeliveryConfig(to=delivery_raw["to"], from_=delivery_raw["from"]),
    )


def load_topics(topics_dir: Path, defaults_path: Path) -> list[TopicConfig]:
    defaults = _load_yaml(defaults_path)
    topics: list[TopicConfig] = []
    for topic_path in sorted(topics_dir.glob("*.yaml")):
        topic_raw = _load_yaml(topic_path)
        merged = _deep_merge(defaults, topic_raw)
        attention = merged.get("attention", {})
        topics.append(
            TopicConfig(
                slug=topic_path.stem,
                name=merged["name"],
                description=merged["description"].strip(),
                keywords=merged["keywords"],
                sources=merged["sources"],
                max_age_days=merged["max_age_days"],
                min_relevance=merged["min_relevance"],
                max_items=merged["max_items"],
                attention_enabled=attention.get("enabled", False),
                attention_min_score_gain=attention.get("min_score_gain", 0),
            )
        )
    return topics


def load_env(path: Path) -> None:
    """Load KEY=VALUE lines from path into os.environ, without overwriting
    variables the real environment already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())
```

- [ ] **Step 7: Write `agent/requirements.txt`**

```
pyyaml
requests
openai
feedparser
```

`feedparser` is unused until TASK-007 but listed now so `pip install -r`
only has to run once for the whole build.

- [ ] **Step 8: Update `.gitignore`**

The current entries anticipate the agent but under the old plan's naming
(`agent/seen.json`) and miss the new `agent/runs/` directory. Replace the
existing agent block:

Old:
```
# Research agent (docs/agent-plan.md) — implementation not started yet,
# but these paths shouldn't be committed once it is.
agent/.env
agent/seen.json
agent/__pycache__/
agent/venv/
```

New:
```
# Research agent (docs/agent-plan.md, docs/superpowers/specs/2026-08-12-research-agent-design.md)
agent/.env
agent/state.json
agent/runs/
agent/__pycache__/
agent/venv/
```

- [ ] **Step 9: Install dependencies**

Run: `pip install -r agent/requirements.txt`

`pyyaml`, `requests`, and `openai` are already present in this
environment's global interpreter; this step installs `feedparser`, the one
new dependency, and confirms `pip` resolves the rest without conflict.

- [ ] **Step 10: Verify config loads and merges correctly**

Run (PowerShell, from `C:\A\polozov`):

```powershell
python -c 'from pathlib import Path; from agent import config; s = config.load_settings(Path("agent/defaults.yaml")); topics = config.load_topics(Path("agent/topics"), Path("agent/defaults.yaml")); print(s); [print(t.slug, t.name, t.max_age_days, t.min_relevance, list(t.sources.keys())) for t in topics]'
```

Expected output: one `Settings(...)` line showing the DeepSeek base URL and
`deepseek-chat`, then three lines — one per topic — each showing the
topic's slug, name, `max_age_days=10`, `min_relevance=6` (both inherited
from `defaults.yaml`, since none of the three topic files override them),
and its source keys (`hacker_news`, `reddit`, `rss`, `releases`, and
`web_search` for `ai-agents` only).

If any topic is missing a key, the merge or the topic file has a typo —
fix before continuing.

- [ ] **Step 11: Commit**

```powershell
git add agent/__init__.py agent/sources/__init__.py agent/sources/base.py agent/config.py agent/defaults.yaml agent/topics/ai-agents.yaml agent/topics/data-viz.yaml agent/topics/full-stack.yaml agent/requirements.txt .gitignore
git commit -m "Scaffold research agent: YAML config, candidate contract"
```

---

## Task 2: Hacker News connector + recency window

**Files:**
- Create: `agent/sources/hn.py`
- Create: `agent/date_guard.py`

**Interfaces:**
- Consumes: `agent.sources.base.Candidate`, `agent.sources.base.Drop`,
  `agent.sources.base.TopicConfig` (Task 1)
- Produces:
  - `agent.sources.hn.collect(topic: TopicConfig, now: datetime) -> tuple[list[Candidate], list[Drop]]`
  - `agent.date_guard.apply_recency_window(candidates: list[Candidate], max_age_days: int, now: datetime) -> tuple[list[Candidate], list[Drop]]`

- [ ] **Step 1: Write `agent/date_guard.py`**

Pure logic, no network — the single place `max_age_days` is enforced,
regardless of whether the source connector already applied a native
filter.

```python
"""Recency window enforcement — the single place max_age_days is checked,
independent of whether a connector already filtered server-side."""

from __future__ import annotations

from datetime import datetime, timedelta

from agent.sources.base import Candidate, Drop


def apply_recency_window(
    candidates: list[Candidate],
    max_age_days: int,
    now: datetime,
) -> tuple[list[Candidate], list[Drop]]:
    """Keep candidates published within max_age_days of now; drop the rest."""
    cutoff = now - timedelta(days=max_age_days)
    kept: list[Candidate] = []
    drops: list[Drop] = []
    for candidate in candidates:
        if candidate.published_at >= cutoff:
            kept.append(candidate)
        else:
            drops.append(
                Drop(
                    url=candidate.url,
                    title=candidate.title,
                    reason="outside_window",
                    detail={
                        "published_at": candidate.published_at.isoformat(),
                        "max_age_days": max_age_days,
                    },
                )
            )
    return kept, drops
```

- [ ] **Step 2: Verify the date guard with synthetic data (no network)**

Run:

```powershell
python -c 'from datetime import datetime, timedelta, timezone; from agent.date_guard import apply_recency_window; from agent.sources.base import Candidate; now = datetime(2026, 8, 12, tzinfo=timezone.utc); fresh = Candidate(url="https://a", title="fresh", source="hn", topic="x", published_at=now - timedelta(days=2), score=100, excerpt=None); stale = Candidate(url="https://b", title="stale", source="hn", topic="x", published_at=now - timedelta(days=20), score=100, excerpt=None); kept, drops = apply_recency_window([fresh, stale], 10, now); assert kept == [fresh], kept; assert len(drops) == 1 and drops[0].reason == "outside_window" and drops[0].detail["max_age_days"] == 10, drops; print("date_guard OK")'
```

Expected output: `date_guard OK`. If the assertion fails, the comparison
direction or the cutoff arithmetic is wrong — fix before continuing.

- [ ] **Step 3: Write `agent/sources/hn.py`**

Queries HN Algolia once per topic keyword, merges hits across keywords by
`objectID` so the same story surfacing under two keywords isn't duplicated,
and applies the native `numericFilters` (points + creation time) so most
filtering happens server-side before any HTTP response body is parsed.

```python
"""Hacker News connector — queries Algolia search per topic keyword."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from agent.sources.base import Candidate, Drop, TopicConfig

ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
EXCERPT_MAX_CHARS = 280


def collect(topic: TopicConfig, now: datetime) -> tuple[list[Candidate], list[Drop]]:
    hn_config = topic.sources.get("hacker_news")
    if hn_config is None:
        return [], []
    min_points = hn_config.get("min_points", 0)
    cutoff_epoch = int((now - timedelta(days=topic.max_age_days)).timestamp())

    hits_by_id: dict[str, dict] = {}
    for keyword in topic.keywords:
        params = {
            "query": keyword,
            "tags": "story",
            "numericFilters": f"created_at_i>{cutoff_epoch},points>={min_points}",
        }
        response = requests.get(ALGOLIA_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        for hit in response.json()["hits"]:
            hits_by_id[hit["objectID"]] = hit

    candidates: list[Candidate] = []
    drops: list[Drop] = []
    for object_id, hit in hits_by_id.items():
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
        title = hit.get("title") or "(untitled)"
        created_at_i = hit.get("created_at_i")
        if created_at_i is None:
            # HN Algolia always populates created_at_i in practice; this
            # branch exists so the connector never invents a date rather
            # than because it's expected to fire.
            drops.append(
                Drop(url=url, title=title, reason="undated", detail={"source": "hn"})
            )
            continue
        excerpt = hit.get("story_text")
        if excerpt:
            excerpt = excerpt[:EXCERPT_MAX_CHARS]
        candidates.append(
            Candidate(
                url=url,
                title=title,
                source="hn",
                topic=topic.slug,
                published_at=datetime.fromtimestamp(created_at_i, tz=timezone.utc),
                score=hit.get("points"),
                excerpt=excerpt,
            )
        )

    return candidates, drops
```

- [ ] **Step 4: Verify against the live Algolia API**

Run (requires network access to `hn.algolia.com`, no API key needed):

```powershell
python -c 'from datetime import datetime, timezone; from pathlib import Path; from agent import config; from agent.sources import hn; topics = config.load_topics(Path("agent/topics"), Path("agent/defaults.yaml")); topic = next(t for t in topics if t.slug == "ai-agents"); candidates, drops = hn.collect(topic, datetime.now(timezone.utc)); print(f"{len(candidates)} candidates, {len(drops)} drops"); [print(c.published_at, c.score, c.title) for c in candidates[:5]]; assert all(c.published_at.tzinfo is not None for c in candidates)'
```

Expected: a non-negative candidate count (zero is possible if nothing
matched the keywords in the last 10 days, but should not error), a handful
of printed titles with recent-looking dates, and no assertion failure. If
the request raises, check network connectivity before assuming the code is
wrong.

- [ ] **Step 5: Commit**

```powershell
git add agent/date_guard.py agent/sources/hn.py
git commit -m "Add Hacker News connector and the recency window guard"
```

---

## Task 3: Dedupe state

**Files:**
- Create: `agent/dedupe.py`

**Interfaces:**
- Consumes: `agent.sources.base.Candidate`, `agent.sources.base.Drop` (Task 1)
- Produces:
  - `agent.dedupe.StateEntry` — dataclass: `first_seen: str`,
    `last_score: int | None`, `times_sent: int`
  - `agent.dedupe.url_hash(url: str) -> str`
  - `agent.dedupe.load_state(path: Path) -> dict[str, StateEntry]`
  - `agent.dedupe.save_state(path: Path, state: dict[str, StateEntry]) -> None`
  - `agent.dedupe.record_seen(state: dict[str, StateEntry], candidate: Candidate, now: datetime) -> None`
  - `agent.dedupe.mark_sent(state: dict[str, StateEntry], candidate: Candidate) -> None`
  - `agent.dedupe.filter_seen(candidates: list[Candidate], state: dict[str, StateEntry]) -> tuple[list[Candidate], list[Drop]]`

- [ ] **Step 1: Write `agent/dedupe.py`**

The store records every candidate seen, whether or not it survives later
filters — that's what lets `last_score` accumulate history for the
attention window built in a later task. `filter_seen` only drops items
that were actually delivered before (`times_sent > 0`); a candidate that
was merely collected-and-dropped in a past run is not a duplicate.

```python
"""Persistent seen-URL state: hashes, first-seen dates, score history, and
send counts. filter_seen only drops items that were actually delivered
before — a candidate that was collected and dropped in a past run is not
a duplicate, and stays eligible."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from agent.sources.base import Candidate, Drop


@dataclass
class StateEntry:
    first_seen: str  # ISO 8601
    last_score: int | None
    times_sent: int


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def load_state(path: Path) -> dict[str, StateEntry]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {key: StateEntry(**value) for key, value in raw.items()}


def save_state(path: Path, state: dict[str, StateEntry]) -> None:
    raw = {key: asdict(entry) for key, entry in state.items()}
    path.write_text(json.dumps(raw, indent=2, sort_keys=True), encoding="utf-8")


def record_seen(state: dict[str, StateEntry], candidate: Candidate, now: datetime) -> None:
    """Update (or create) the state entry for a candidate. Called for
    every candidate collected this run, whether or not it survives later
    filters — this is how score history accumulates for items that are
    outside the window or below threshold today but might not be next
    week."""
    key = url_hash(candidate.url)
    entry = state.get(key)
    if entry is None:
        state[key] = StateEntry(first_seen=now.isoformat(), last_score=candidate.score, times_sent=0)
    else:
        entry.last_score = candidate.score


def mark_sent(state: dict[str, StateEntry], candidate: Candidate) -> None:
    """Called once a candidate has actually been delivered. Requires
    record_seen to have already run for this candidate in the same run —
    a KeyError here means the pipeline sent something it never recorded,
    which is a bug worth surfacing loudly rather than papering over."""
    state[url_hash(candidate.url)].times_sent += 1


def filter_seen(
    candidates: list[Candidate],
    state: dict[str, StateEntry],
) -> tuple[list[Candidate], list[Drop]]:
    kept: list[Candidate] = []
    drops: list[Drop] = []
    for candidate in candidates:
        entry = state.get(url_hash(candidate.url))
        if entry is not None and entry.times_sent > 0:
            drops.append(
                Drop(
                    url=candidate.url,
                    title=candidate.title,
                    reason="seen",
                    detail={"times_sent": entry.times_sent},
                )
            )
        else:
            kept.append(candidate)
    return kept, drops
```

- [ ] **Step 2: Verify state round-trips and dedupe semantics are correct**

Run:

```powershell
python -c 'import tempfile; from pathlib import Path; from datetime import datetime, timezone; from agent import dedupe; from agent.sources.base import Candidate; now = datetime(2026, 8, 12, tzinfo=timezone.utc); c1 = Candidate(url="https://a", title="a", source="hn", topic="x", published_at=now, score=50, excerpt=None); c2 = Candidate(url="https://b", title="b", source="hn", topic="x", published_at=now, score=10, excerpt=None); state = {}; dedupe.record_seen(state, c1, now); dedupe.record_seen(state, c2, now); dedupe.mark_sent(state, c1); kept, drops = dedupe.filter_seen([c1, c2], state); assert kept == [c2], kept; assert len(drops) == 1 and drops[0].reason == "seen" and drops[0].detail["times_sent"] == 1, drops; tmp = Path(tempfile.mktemp(suffix=".json")); dedupe.save_state(tmp, state); reloaded = dedupe.load_state(tmp); assert reloaded[dedupe.url_hash("https://a")].times_sent == 1; tmp.unlink(); print("dedupe OK")'
```

Expected: `dedupe OK`. This checks that a sent item is dropped as `seen` on
a later pass, an unsent item is kept, and state survives a save/load
round-trip.

- [ ] **Step 3: Commit**

```powershell
git add agent/dedupe.py
git commit -m "Add dedupe state store with times_sent-based filtering"
```

---

## Task 4: Event stream + dry run

**Files:**
- Create: `agent/events.py`
- Create: `agent/main.py`
- Create: `agent/__main__.py`

**Interfaces:**
- Consumes: `Candidate`, `Drop`, `TopicConfig` (Task 1); `hn.collect`,
  `apply_recency_window` (Task 2); `load_state`, `save_state`,
  `record_seen`, `filter_seen` (Task 3)
- Produces:
  - `agent.events.new_run_id(now: datetime) -> str`
  - `agent.events.EventWriter` — `.emit(stage, event, **fields)`,
    `.emit_candidate(stage, source, topic, candidate)`,
    `.emit_drop(stage, topic, drop)`, `.close()`, `.path: Path`
  - `agent.main.run_dry(topic_filter: str | None) -> None`
  - CLI: `python -m agent --dry-run [--topic SLUG]`

- [ ] **Step 1: Write `agent/events.py`**

One JSON object per line, one file per run, written to `agent/runs/`. This
is the substrate both the terminal renderer in this task and the run panel
(separate spec) read from — nothing downstream computes anything the event
stream doesn't already carry.

```python
"""JSONL event emitter for pipeline runs — the substrate for --dry-run
output, the real-run log, and the future run panel."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.sources.base import Candidate, Drop

RUNS_DIR = Path(__file__).parent / "runs"


def new_run_id(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H%MZ")


class EventWriter:
    """Appends one JSON object per line to agent/runs/<run_id>.jsonl."""

    def __init__(self, run_id: str, runs_dir: Path = RUNS_DIR) -> None:
        runs_dir.mkdir(parents=True, exist_ok=True)
        self.path = runs_dir / f"{run_id}.jsonl"
        self._file = self.path.open("a", encoding="utf-8")

    def emit(self, stage: str, event: str, **fields: Any) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "event": event,
            **fields,
        }
        self._file.write(json.dumps(record, sort_keys=True) + "\n")
        self._file.flush()

    def emit_candidate(self, stage: str, source: str, topic: str, candidate: Candidate) -> None:
        self.emit(
            stage,
            "candidate",
            source=source,
            topic=topic,
            url=candidate.url,
            title=candidate.title,
        )

    def emit_drop(self, stage: str, topic: str, drop: Drop) -> None:
        self.emit(
            stage,
            "drop",
            topic=topic,
            url=drop.url,
            title=drop.title,
            reason=drop.reason,
            detail=drop.detail,
        )

    def close(self) -> None:
        self._file.close()


def read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
```

- [ ] **Step 2: Write `agent/main.py`**

Wires config, the HN connector, the date guard, and dedupe into a per-topic
funnel, emitting events at every stage. `--dry-run` is the only mode this
task builds; a real (delivering) mode is added in Task 6.

```python
"""Entry point: python -m agent --dry-run [--topic SLUG]"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from agent import config, dedupe, date_guard, events
from agent.sources import hn

AGENT_DIR = Path(__file__).parent
DEFAULTS_PATH = AGENT_DIR / "defaults.yaml"
TOPICS_DIR = AGENT_DIR / "topics"
STATE_PATH = AGENT_DIR / "state.json"

CONNECTORS = {
    "hacker_news": hn.collect,
}


def run_dry(topic_filter: str | None) -> None:
    now = datetime.now(timezone.utc)
    run_id = events.new_run_id(now)
    writer = events.EventWriter(run_id)

    topics = config.load_topics(TOPICS_DIR, DEFAULTS_PATH)
    if topic_filter:
        topics = [t for t in topics if t.slug == topic_filter]
        if not topics:
            print(f"No topic named {topic_filter!r}", file=sys.stderr)
            sys.exit(1)

    state = dedupe.load_state(STATE_PATH)

    for topic in topics:
        counts: Counter[str] = Counter()
        all_candidates = []
        for source_name, connector in CONNECTORS.items():
            if source_name not in topic.sources:
                continue
            candidates, drops = connector(topic, now)
            counts["collected"] += len(candidates) + len(drops)
            for candidate in candidates:
                writer.emit_candidate("collect", source_name, topic.slug, candidate)
                dedupe.record_seen(state, candidate, now)
            for drop in drops:
                writer.emit_drop("collect", topic.slug, drop)
            all_candidates.extend(candidates)
        counts["dated"] = len(all_candidates)

        kept, drops = date_guard.apply_recency_window(all_candidates, topic.max_age_days, now)
        for drop in drops:
            writer.emit_drop("date_guard", topic.slug, drop)
        counts["in_window"] = len(kept)

        kept, drops = dedupe.filter_seen(kept, state)
        for drop in drops:
            writer.emit_drop("dedupe", topic.slug, drop)
        counts["new"] = len(kept)

        _print_funnel(topic.name, counts)

    dedupe.save_state(STATE_PATH, state)
    writer.close()
    print(f"\nRun recorded: {writer.path}")


def _print_funnel(topic_name: str, counts: Counter[str]) -> None:
    print(f"\n{topic_name}")
    print(
        f"  collected {counts['collected']} -> dated {counts['dated']} "
        f"-> in-window {counts['in_window']} -> new {counts['new']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m agent")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--topic", default=None)
    args = parser.parse_args()

    config.load_env(AGENT_DIR / ".env")

    if args.dry_run:
        run_dry(args.topic)
    else:
        parser.error("only --dry-run is implemented so far; real delivery lands in Task 6")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write `agent/__main__.py`**

Makes `python -m agent` resolve to `main.main()`.

```python
from agent.main import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify the dry run end to end**

Run (from `C:\A\polozov`, requires network access to `hn.algolia.com`):

```powershell
python -m agent --dry-run --topic ai-agents
```

Expected: a funnel line like
`AI Agents & Engineering` /
`  collected N -> dated N -> in-window M -> new M` (numbers depend on
what's currently on HN), followed by `Run recorded: ...\agent\runs\....jsonl`.
No candidates lost between `collected` and `dated` is expected here since
`hn.collect` currently only produces the `undated` drop in a defensive
branch that HN never actually triggers.

- [ ] **Step 5: Verify the event file contents**

Run:

```powershell
python -c 'import glob; from agent.events import read_events; path = sorted(glob.glob("agent/runs/*.jsonl"))[-1]; events_ = read_events(path); stages = {e["stage"] for e in events_}; print(path, len(events_), "events across stages:", stages); assert "collect" in stages; assert all("ts" in e for e in events_); print("events OK")'
```

Expected: a printed path, an event count greater than zero, at least the
`collect` stage present, and `events OK`.

- [ ] **Step 6: Verify a tightened window increases drops with correct detail**

Confirms the recency window is genuinely wired end-to-end and that drop
events carry both threshold and actual value, per the spec's own
verification requirement for the date guard.

Run:

```powershell
python -c '
import shutil
from pathlib import Path
shutil.copy("agent/topics/ai-agents.yaml", "agent/topics/ai-agents.yaml.bak")
text = Path("agent/topics/ai-agents.yaml").read_text()
Path("agent/topics/ai-agents.yaml").write_text(text + "\nmax_age_days: 1\n")
'
python -m agent --dry-run --topic ai-agents
python -c 'import glob; from agent.events import read_events; path = sorted(glob.glob("agent/runs/*.jsonl"))[-1]; drops = [e for e in read_events(path) if e.get("reason") == "outside_window"]; assert all("max_age_days" in e["detail"] and "published_at" in e["detail"] for e in drops), drops; print(len(drops), "outside_window drops, all with detail")'
python -c 'from pathlib import Path; import shutil; shutil.move("agent/topics/ai-agents.yaml.bak", "agent/topics/ai-agents.yaml")'
```

Expected: a drop count (likely higher than the previous run's `in-window`
figure moving toward zero, since `max_age_days: 1` is aggressive), and no
assertion error. The last command restores `ai-agents.yaml` to its
committed form — verify with `git status` that the file shows no diff
before continuing.

- [ ] **Step 7: Commit**

```powershell
git add agent/events.py agent/main.py agent/__main__.py
git commit -m "Add event stream and --dry-run pipeline"
```

---

## Task 5: DeepSeek ranking

**Files:**
- Create: `agent/summarize.py`

**Interfaces:**
- Consumes: `Candidate`, `TopicConfig` (Task 1); `Settings`,
  `LLMConfig` (Task 1/config.py)
- Produces:
  - `agent.summarize.RankedItem` — frozen dataclass: `candidate: Candidate`,
    `summary: str`, `score: int`
  - `agent.summarize.rank_topic(topic: TopicConfig, candidates: list[Candidate], settings: Settings) -> list[RankedItem]`

- [ ] **Step 1: Confirm the DeepSeek model id and JSON-mode behaviour**

Before writing code, check DeepSeek's current API documentation for the
active chat model id (`deepseek-chat` is the value already in
`defaults.yaml`, carried over from the spec) and confirm
`response_format={"type": "json_object"}` is still supported on the
`openai`-SDK-compatible endpoint at `https://api.deepseek.com`. If the
model id has changed, update `agent/defaults.yaml`'s `llm.model` value
before continuing — do not hardcode a different value in `summarize.py`.

- [ ] **Step 2: Write `agent/summarize.py`**

One batched call per topic. The response is validated against the sent
candidate set — right id range, no duplicates, every id present, score in
range — because DeepSeek's JSON mode guarantees syntactically valid JSON,
not a JSON *shape* matching what was asked for. A validation failure
retries once; two failures fall back to one call per candidate so a single
malformed batch costs one topic's ordering, not the whole run.

```python
"""DeepSeek-backed ranking: one batched call per topic, validated and
retried before falling back to per-candidate calls."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from openai import OpenAI

from agent.config import Settings
from agent.sources.base import Candidate, TopicConfig

# The word "json" must appear in the prompt for DeepSeek's JSON object
# response mode to accept the request — this phrasing satisfies that
# requirement incidentally, since it's also what we want the model to do.
RANK_SYSTEM_PROMPT = (
    "You rank candidate links for a weekly research digest against one "
    "topic. For each candidate, judge relevance to the topic on a 1-10 "
    "scale and write a one-sentence summary. Respond with JSON only: an "
    'object of the shape {"rankings": [{"id": 1, "summary": "...", '
    '"score": 7}, ...]}, one entry per candidate, in the order given, '
    "ids starting at 1."
)


@dataclass(frozen=True)
class RankedItem:
    candidate: Candidate
    summary: str
    score: int


def _client(settings: Settings) -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    return OpenAI(base_url=settings.llm.base_url, api_key=api_key)


def _build_batch_prompt(topic: TopicConfig, candidates: list[Candidate]) -> str:
    lines = [f"Topic: {topic.name}", f"Description: {topic.description}", "", "Candidates:"]
    for index, candidate in enumerate(candidates, start=1):
        excerpt = f" — {candidate.excerpt}" if candidate.excerpt else ""
        lines.append(f"{index}. [{candidate.source}] {candidate.title}{excerpt}")
    return "\n".join(lines)


def _parse_batch_response(raw: str, expected_count: int) -> list[dict] | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or "rankings" not in parsed:
        return None
    rankings = parsed["rankings"]
    if not isinstance(rankings, list) or len(rankings) != expected_count:
        return None
    seen_ids: set[int] = set()
    for entry in rankings:
        if not isinstance(entry, dict) or not {"id", "summary", "score"} <= entry.keys():
            return None
        entry_id = entry["id"]
        if not isinstance(entry_id, int) or not (1 <= entry_id <= expected_count):
            return None
        if entry_id in seen_ids:
            return None
        seen_ids.add(entry_id)
        if not isinstance(entry["score"], int) or not (1 <= entry["score"] <= 10):
            return None
        if not isinstance(entry["summary"], str) or not entry["summary"].strip():
            return None
    if seen_ids != set(range(1, expected_count + 1)):
        return None
    return rankings


def _call_batch(
    client: OpenAI, settings: Settings, topic: TopicConfig, candidates: list[Candidate]
) -> list[dict] | None:
    response = client.chat.completions.create(
        model=settings.llm.model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": RANK_SYSTEM_PROMPT},
            {"role": "user", "content": _build_batch_prompt(topic, candidates)},
        ],
    )
    content = response.choices[0].message.content or ""
    return _parse_batch_response(content, len(candidates))


def rank_topic(topic: TopicConfig, candidates: list[Candidate], settings: Settings) -> list[RankedItem]:
    if not candidates:
        return []
    client = _client(settings)

    result = _call_batch(client, settings, topic, candidates)
    if result is None:
        result = _call_batch(client, settings, topic, candidates)  # one retry

    if result is not None:
        by_id = {entry["id"]: entry for entry in result}
        return [
            RankedItem(candidate=c, summary=by_id[i]["summary"], score=by_id[i]["score"])
            for i, c in enumerate(candidates, start=1)
        ]

    # Batch failed twice — fall back to one call per candidate so the
    # whole topic doesn't lose its ranking over one malformed response.
    ranked: list[RankedItem] = []
    for candidate in candidates:
        single = _call_batch(client, settings, topic, [candidate])
        if single is None:
            ranked.append(RankedItem(candidate=candidate, summary="(ranking failed)", score=1))
        else:
            entry = single[0]
            ranked.append(RankedItem(candidate=candidate, summary=entry["summary"], score=entry["score"]))
    return ranked
```

- [ ] **Step 3: Verify the response validator with synthetic strings (no network)**

Run:

```powershell
python -c '
from agent.summarize import _parse_batch_response
valid = "{\"rankings\": [{\"id\": 1, \"summary\": \"a\", \"score\": 7}, {\"id\": 2, \"summary\": \"b\", \"score\": 3}]}"
assert _parse_batch_response(valid, 2) is not None, "valid input rejected"
assert _parse_batch_response("not json", 2) is None, "garbage accepted"
assert _parse_batch_response("{\"rankings\": []}", 2) is None, "wrong length accepted"
missing_field = "{\"rankings\": [{\"id\": 1, \"summary\": \"a\"}]}"
assert _parse_batch_response(missing_field, 1) is None, "missing field accepted"
duplicate_id = "{\"rankings\": [{\"id\": 1, \"summary\": \"a\", \"score\": 5}, {\"id\": 1, \"summary\": \"b\", \"score\": 6}]}"
assert _parse_batch_response(duplicate_id, 2) is None, "duplicate id accepted"
out_of_range = "{\"rankings\": [{\"id\": 1, \"summary\": \"a\", \"score\": 11}]}"
assert _parse_batch_response(out_of_range, 1) is None, "out-of-range score accepted"
print("validator OK")
'
```

Expected: `validator OK`. This is the free half of Task 5's verification —
no `DEEPSEEK_API_KEY` needed.

- [ ] **Step 4: Verify against the live DeepSeek API — first paid call**

Requires `DEEPSEEK_API_KEY` set in `agent/.env` or the real environment.
This is the first step in the whole build that spends money — expect a
fraction of a cent for a handful of items.

Run:

```powershell
python -c '
from datetime import datetime, timezone
from pathlib import Path
from agent import config
from agent.sources import hn
from agent.summarize import rank_topic

config.load_env(Path("agent/.env"))
settings = config.load_settings(Path("agent/defaults.yaml"))
topics = config.load_topics(Path("agent/topics"), Path("agent/defaults.yaml"))
topic = next(t for t in topics if t.slug == "ai-agents")
candidates, _ = hn.collect(topic, datetime.now(timezone.utc))
sample = candidates[:5]
if not sample:
    print("no live candidates to rank right now — rerun later or against a different topic")
else:
    ranked = rank_topic(topic, sample, settings)
    assert len(ranked) == len(sample)
    for item in ranked:
        print(item.score, item.summary, item.candidate.title)
    print("ranking OK")
'
```

Expected: one line per sampled candidate showing an integer score
(1–10), a one-sentence summary, and the title, followed by `ranking OK`. If
`DEEPSEEK_API_KEY` is unset, this raises `RuntimeError` — set it in
`agent/.env` (not committed) before retrying.

- [ ] **Step 5: Commit**

```powershell
git add agent/summarize.py
git commit -m "Add batched DeepSeek ranking with validated fallback"
```

---

## Task 6: Digest, delivery, real run, doc sync — v1 ships

**Files:**
- Create: `agent/digest.py`
- Create: `agent/deliver.py`
- Modify: `agent/main.py`
- Modify: `docs/agent-plan.md`
- Modify: `researcher/agent.html`

**Interfaces:**
- Consumes: `RankedItem` (Task 5); `Settings`, `DeliveryConfig` (Task 1);
  `EventWriter`, `Drop` (Tasks 1, 4)
- Produces:
  - `agent.digest.build(ranked_by_topic: dict[str, list[RankedItem]]) -> tuple[str, str]`
    (subject, body)
  - `agent.deliver.send(subject: str, body: str, settings: Settings) -> None`
  - `agent.main.run_real(topic_filter: str | None) -> None`
  - CLI: `python -m agent [--topic SLUG]` (no `--dry-run`) sends a real digest

- [ ] **Step 1: Write `agent/digest.py`**

```python
"""Assemble ranked items into the weekly digest email body."""

from __future__ import annotations

from agent.summarize import RankedItem


def build(ranked_by_topic: dict[str, list[RankedItem]]) -> tuple[str, str]:
    """Return (subject, plain-text body)."""
    lines = ["Weekly research digest", ""]
    total = 0
    for topic_name, items in ranked_by_topic.items():
        if not items:
            continue
        lines.append(topic_name)
        lines.append("-" * len(topic_name))
        for item in items:
            lines.append(f"- {item.candidate.title}")
            lines.append(f"  {item.summary}")
            lines.append(f"  {item.candidate.url}")
            total += 1
        lines.append("")

    subject = f"Research digest — {total} items" if total else "Research digest — nothing new this week"
    return subject, "\n".join(lines)
```

- [ ] **Step 2: Write `agent/deliver.py`**

```python
"""SMTP delivery for the weekly digest."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from agent.config import Settings


def send(subject: str, body: str, settings: Settings) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.delivery.from_
    message["To"] = settings.delivery.to
    message.set_content(body)

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(message)
```

- [ ] **Step 3: Add `run_real` to `agent/main.py`**

Extends the collect → date-guard → dedupe funnel from Task 4 with ranking,
threshold/cap filtering (each with its own drop event and reason), digest
assembly, and delivery. Only items that are actually sent get
`dedupe.mark_sent` called on them.

Modify `agent/main.py`: add the `summarize`, `digest`, and `deliver`
imports, add `run_real`, and replace the `parser.error(...)` branch in
`main()` with a call to it.

```python
from agent import config, dedupe, date_guard, deliver, digest, events, summarize
from agent.sources import hn
from agent.sources.base import Drop
```

(Replaces the existing `from agent import config, dedupe, date_guard, events`
import line.)

```python
def run_real(topic_filter: str | None) -> None:
    now = datetime.now(timezone.utc)
    run_id = events.new_run_id(now)
    writer = events.EventWriter(run_id)

    settings = config.load_settings(DEFAULTS_PATH)
    topics = config.load_topics(TOPICS_DIR, DEFAULTS_PATH)
    if topic_filter:
        topics = [t for t in topics if t.slug == topic_filter]
        if not topics:
            print(f"No topic named {topic_filter!r}", file=sys.stderr)
            sys.exit(1)

    state = dedupe.load_state(STATE_PATH)
    ranked_by_topic: dict[str, list[summarize.RankedItem]] = {}

    for topic in topics:
        all_candidates = []
        for source_name, connector in CONNECTORS.items():
            if source_name not in topic.sources:
                continue
            candidates, drops = connector(topic, now)
            for candidate in candidates:
                writer.emit_candidate("collect", source_name, topic.slug, candidate)
                dedupe.record_seen(state, candidate, now)
            for drop in drops:
                writer.emit_drop("collect", topic.slug, drop)
            all_candidates.extend(candidates)

        kept, drops = date_guard.apply_recency_window(all_candidates, topic.max_age_days, now)
        for drop in drops:
            writer.emit_drop("date_guard", topic.slug, drop)

        kept, drops = dedupe.filter_seen(kept, state)
        for drop in drops:
            writer.emit_drop("dedupe", topic.slug, drop)

        ranked = summarize.rank_topic(topic, kept, settings)
        ranked.sort(key=lambda item: item.score, reverse=True)

        above_threshold, below_threshold = [], []
        for item in ranked:
            (above_threshold if item.score >= topic.min_relevance else below_threshold).append(item)
        for item in below_threshold:
            writer.emit_drop(
                "rank",
                topic.slug,
                Drop(
                    url=item.candidate.url,
                    title=item.candidate.title,
                    reason="below_relevance",
                    detail={"score": item.score, "min_relevance": topic.min_relevance},
                ),
            )

        keep = above_threshold[: topic.max_items]
        over_limit = above_threshold[topic.max_items :]
        for item in over_limit:
            writer.emit_drop(
                "rank",
                topic.slug,
                Drop(
                    url=item.candidate.url,
                    title=item.candidate.title,
                    reason="over_max_items",
                    detail={"max_items": topic.max_items},
                ),
            )

        ranked_by_topic[topic.name] = keep

    subject, body = digest.build(ranked_by_topic)
    total_items = sum(len(items) for items in ranked_by_topic.values())

    if total_items:
        deliver.send(subject, body, settings)
        for items in ranked_by_topic.values():
            for item in items:
                dedupe.mark_sent(state, item.candidate)
        writer.emit("deliver", "sent", detail={"items": total_items, "topics": len(ranked_by_topic)})
        print(f"Sent {total_items} items across {len(ranked_by_topic)} topics.")
    else:
        writer.emit("deliver", "skipped", detail={"reason": "nothing_to_send"})
        print("Nothing to send.")

    dedupe.save_state(STATE_PATH, state)
    writer.close()
    print(f"Run recorded: {writer.path}")
```

In `main()`, replace:

```python
    if args.dry_run:
        run_dry(args.topic)
    else:
        parser.error("only --dry-run is implemented so far; real delivery lands in Task 6")
```

with:

```python
    if args.dry_run:
        run_dry(args.topic)
    else:
        run_real(args.topic)
```

- [ ] **Step 4: Verify digest assembly and SMTP delivery in isolation**

Run:

```powershell
python -c '
from agent.digest import build
from agent.summarize import RankedItem
from agent.sources.base import Candidate
from datetime import datetime, timezone

c = Candidate(url="https://example.com/a", title="Example", source="hn", topic="ai-agents", published_at=datetime.now(timezone.utc), score=100, excerpt=None)
item = RankedItem(candidate=c, summary="A one-line summary.", score=8)
subject, body = build({"AI Agents & Engineering": [item]})
assert "1 items" in subject
assert "Example" in body and "A one-line summary." in body and c.url in body
print(subject)
print(body)
print("digest OK")
'
```

Expected: the subject line, the full body text, and `digest OK`. This
checks assembly only — no SMTP call, no network.

- [ ] **Step 5: Verify one full real run**

Requires `DEEPSEEK_API_KEY` and SMTP credentials
(`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`) in `agent/.env`. This
is the run that actually sends mail — check the inbox at
`delivery.to` (`hypnosisflow@gmail.com` per `defaults.yaml`) after it
completes.

Run:

```powershell
python -m agent --topic ai-agents
```

Expected: either `Sent N items across 1 topics.` followed by a real email
arriving at the configured inbox with topic-grouped items, one-line
summaries, and links — or `Nothing to send.` if everything currently on HN
for this topic is below `min_relevance` or already sent. Either outcome is
a pass; a raised exception is not — read the traceback, it will point at
whichever credential or field is missing.

- [ ] **Step 6: Update `docs/agent-plan.md`**

This document's Sources, Pipeline, Proposed stack, Proposed module layout,
Task breakdown, Environment/secrets, and Status sections are superseded by
`docs/superpowers/specs/2026-08-12-research-agent-design.md`. Replace them
so the two documents don't drift, per `CLAUDE.md`'s instruction to keep
them in sync at a high level.

Replace the `## Sources` section (currently listing four sources) with:

```markdown
## Sources

- Hacker News — public Algolia search API, filtered to each topic's keywords.
- Blog and RSS feeds — a curated list maintained by hand, one per topic.
- Repo release watching — GitHub releases API for a handful of watched repos per topic; a version bump is unambiguous news.
- A handful of subreddits per topic — chosen once, revisited later if the signal is bad.
- Web search — broad net via a dedicated search API with a freshness filter (not Claude's built-in web search, which has no date parameter), catches whatever isn't covered above.

Every source returns a publish date for each candidate; undated candidates
are dropped rather than passed through. Full detail:
`docs/superpowers/specs/2026-08-12-research-agent-design.md`.
```

Replace the `## Pipeline` section with:

```markdown
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
```

Replace the `## Proposed stack` section with:

```markdown
## Proposed stack

- A single Python script, run on a schedule rather than a long-lived service.
- `feedparser` for RSS/blog sources; the Hacker News Algolia API, Reddit's public JSON endpoints, and the GitHub releases API for the other aggregators; a dedicated search API (Brave) for the broad net, chosen because it returns a publish date per result.
- A flat JSON file (or SQLite if it outgrows that) holding seen-URL hashes and score history.
- DeepSeek for summarization and relevance scoring, via the OpenAI-compatible `openai` SDK — cheap enough at this volume that ranking quality, not price, is the thing to tune.
- Windows Task Scheduler for the trigger (this repo has no GitHub remote); SMTP for delivery.
```

Replace the `## Proposed module layout` section (everything from that
heading through the module tree) with:

```markdown
## Proposed module layout

See `docs/superpowers/specs/2026-08-12-research-agent-design.md` for the
current module layout, YAML control surface, and candidate/event
contracts — this section is superseded there.
```

Replace the `## Environment / secrets needed` section with:

```markdown
## Environment / secrets needed

- `DEEPSEEK_API_KEY` — DeepSeek, for summarization/ranking.
- `BRAVE_API_KEY` — the web search connector.
- `GITHUB_TOKEN` — optional; raises the release-watching connector's rate limit.
- SMTP host, port, user, password — delivery.

`agent/.env` is gitignored.
```

Replace the `## Task breakdown for the first build session` section with:

```markdown
## Task breakdown for the first build session

Superseded by the build order in
`docs/superpowers/specs/2026-08-12-research-agent-design.md`. As of this
writing, TASK-001 through TASK-006 are complete — the agent runs
end-to-end on Hacker News only, ranked by DeepSeek and delivered by email.
Reddit, RSS, release watching, web search, the attention window,
scheduling, and self-refreshing keywords remain.
```

In the `## Open questions` section, replace the "Where it runs" bullet:

Old:
```
- Where it runs — a scheduled GitHub Action costs nothing and needs no server, but secrets have to live somewhere (GitHub Actions secrets, most likely).
```

New:
```
- Where it runs — resolved: Windows Task Scheduler (this repo has no GitHub remote), secrets in `agent/.env`.
```

Replace the `## Status` section:

Old:
```markdown
## Status

Planning complete. Implementation not started. Pick up at **TASK-001**.
```

New:
```markdown
## Status

v1 shipped: collect (Hacker News) → recency window → dedupe → rank
(DeepSeek) → assemble → deliver (SMTP), running by hand. Remaining
sources, scheduling, and the attention window are tracked in
`docs/superpowers/specs/2026-08-12-research-agent-design.md`.
```

- [ ] **Step 7: Update `researcher/agent.html`**

Same substance, site narrative tone. Replace the `<h2 id="sources">`
section:

Old:
```html
        <h2 id="sources"><span class="num">02</span>Sources</h2>
        <p>Four kinds of source, each with a different signal-to-noise ratio:</p>
        <ul>
          <li>Web search — broad net, catches whatever isn't already covered below.</li>
          <li>Hacker News — via the public Algolia search API, filtered to each topic's keywords.</li>
          <li>A handful of subreddits per topic — chosen once, revisited later if the signal is bad.</li>
          <li>Blog and RSS feeds — a curated list maintained by hand, the highest-signal source once it exists.</li>
        </ul>
```

New:
```html
        <h2 id="sources"><span class="num">02</span>Sources</h2>
        <p>Five kinds of source, each with a different signal-to-noise ratio:</p>
        <ul>
          <li>Hacker News — via the public Algolia search API, filtered to each topic's keywords.</li>
          <li>Blog and RSS feeds — a curated list maintained by hand, the highest-signal source once it exists.</li>
          <li>Repo releases — a version bump on a handful of watched repos per topic is unambiguous news in a way a blog post isn't.</li>
          <li>A handful of subreddits per topic — chosen once, revisited later if the signal is bad.</li>
          <li>Web search — broad net via a search API with a freshness filter, catches whatever isn't already covered above.</li>
        </ul>
        <p>
          Every source has to return a publish date for anything it surfaces —
          undated items get dropped rather than risk something stale reading
          as current.
        </p>
```

Replace the `<h2 id="pipeline">` section:

Old:
```html
        <h2 id="pipeline"><span class="num">03</span>Pipeline</h2>
        <p>Five stages, each one a small, replaceable piece:</p>
        <ul>
          <li>Collect — each source connector runs independently and returns a flat list of candidate links.</li>
          <li>Dedupe — every link's URL gets hashed against a store of what's already been sent; only new links continue.</li>
          <li>Summarize &amp; rank — an LLM reads each candidate against the three topic descriptions and returns a one-line summary plus a relevance score; anything below the threshold gets dropped.</li>
          <li>Assemble — surviving items get grouped by topic into a digest, ordered by relevance within each group.</li>
          <li>Deliver — the digest goes out by email on a fixed schedule.</li>
        </ul>
```

New:
```html
        <h2 id="pipeline"><span class="num">03</span>Pipeline</h2>
        <p>Six stages, each one a small, replaceable piece:</p>
        <ul>
          <li>Collect — each source connector runs independently and returns a flat list of candidate links, each with a publish date.</li>
          <li>Recency window — anything published outside the topic's freshness window gets dropped, unless it's since gained enough traction to earn a second look.</li>
          <li>Dedupe — every link's URL gets hashed against a store of what's already been sent; only new links continue.</li>
          <li>Rank — one call per topic reads that topic's whole surviving batch at once and ranks it, rather than scoring each item in isolation, so "relevant this week" means the same thing every week; a one-line summary and score come back per item, and anything below the threshold or past the per-topic cap gets dropped.</li>
          <li>Assemble — surviving items get grouped by topic into a digest, ordered by relevance within each group.</li>
          <li>Deliver — the digest goes out by email on a fixed schedule.</li>
        </ul>
```

Replace the `<h2 id="stack">` section:

Old:
```html
        <h2 id="stack"><span class="num">04</span>Proposed stack</h2>
        <ul>
          <li>A single Python script, run on a schedule rather than a long-lived service — nothing here needs to be always-on.</li>
          <li><code>feedparser</code> for RSS/blog sources, the Hacker News Algolia API and Reddit's public JSON endpoints for the aggregators, a web search API (or Claude's built-in web search) for the broad net.</li>
          <li>A flat JSON file (or SQLite if it outgrows that) holding seen-URL hashes — the whole point of dedupe is state that survives between runs.</li>
          <li>Claude for summarization and relevance scoring — the same model already writing LAB posts, reused for a much smaller job.</li>
          <li>A scheduled GitHub Action or plain cron for the trigger; SMTP or a transactional email API (Resend) for delivery.</li>
        </ul>
```

New:
```html
        <h2 id="stack"><span class="num">04</span>Proposed stack</h2>
        <ul>
          <li>A single Python script, run on a schedule rather than a long-lived service — nothing here needs to be always-on.</li>
          <li><code>feedparser</code> for RSS/blog sources, the Hacker News Algolia API, Reddit's public JSON endpoints, and the GitHub releases API for the aggregators, a search API with a freshness filter for the broad net.</li>
          <li>A flat JSON file (or SQLite if it outgrows that) holding seen-URL hashes and score history — the whole point of dedupe is state that survives between runs.</li>
          <li>DeepSeek for summarization and relevance scoring — cheap enough at this volume that ranking quality is the thing worth tuning, not price.</li>
          <li>Windows Task Scheduler for the trigger; SMTP for delivery.</li>
        </ul>
```

Replace the `<h2 id="open-questions">` section:

Old:
```html
        <h2 id="open-questions">What's still open</h2>
        <ul>
          <li>Daily vs weekly — start weekly, watch whether Friday's digest already feels stale by Wednesday.</li>
          <li>Resurfacing — a link dismissed once shouldn't come back next week just because dedupe only tracks URLs verbatim.</li>
          <li>Where it runs — a scheduled GitHub Action costs nothing and needs no server, but secrets (search API key, email credentials) have to live somewhere.</li>
          <li>Budget — search and LLM calls both cost money per run; weekly cadence keeps this small, but the number should get watched once it's real.</li>
        </ul>
```

New:
```html
        <h2 id="open-questions">What's still open</h2>
        <ul>
          <li>Daily vs weekly — start weekly, watch whether Friday's digest already feels stale by Wednesday.</li>
          <li>Resurfacing — a link dismissed once shouldn't come back next week just because dedupe only tracks URLs verbatim.</li>
          <li>Budget — search and LLM calls both cost money per run; weekly cadence keeps this small, but the number should get watched once it's real.</li>
        </ul>
```

Replace the `<h2 id="status">` section:

Old:
```html
        <h2 id="status">Status</h2>
        <p>Planning — not yet built. This page is where the plan lives and changes as it gets built.</p>
```

New:
```html
        <h2 id="status">Status</h2>
        <p>
          Building — the pipeline runs end to end on Hacker News alone: collect,
          filter for recency, dedupe, rank with DeepSeek, assemble, and deliver
          by email. Reddit, RSS, release watching, and web search are next.
        </p>
```

- [ ] **Step 8: Verify the site page still renders**

No build step for the site — verify with a local server and `curl`, per
`CLAUDE.md`'s established pattern.

Run (from `C:\A\polozov`, in a separate terminal or background process):

```powershell
python -m http.server 5678 --bind 127.0.0.1
```

Then, in another terminal:

```powershell
curl.exe -s http://127.0.0.1:5678/researcher/agent.html | Select-String "Six stages|DeepSeek|Windows Task Scheduler"
```

Expected: three matching lines, confirming the new copy landed. Stop the
`http.server` process afterward.

- [ ] **Step 9: Commit**

Two commits — one for the shipped code, one for the doc sync — since they're
reviewable independently and a reviewer might accept the code while wanting
wording changes to the docs.

```powershell
git add agent/digest.py agent/deliver.py agent/main.py
git commit -m "Wire ranking, digest assembly, and SMTP delivery — v1 ships"
```

```powershell
git add docs/agent-plan.md researcher/agent.html
git commit -m "Sync agent-plan.md and researcher/agent.html with v1's actual design"
```

---

## Self-Review Notes

**Spec coverage:** Every numbered TASK-001–006 row in the spec's build-order
table maps to a task above. The candidate contract, freshness mechanisms
(hard window; attention window's state-recording half, since the rescue
logic itself is TASK-009 and explicitly out of scope), dedupe semantics
(including the `times_sent` fix from the spec's self-review), batched
ranking with validation/retry/fallback, the event stream and its closed
drop-reason set, SMTP delivery, and the doc-sync requirement are all
covered. Reddit, RSS, releases, web search, the attention rescue itself,
scheduling, and `suggest-keywords` are correctly left out (TASK-007
onward).

**Placeholder scan:** No TBD/TODO markers; every code block is complete and
runnable as shown; every step's verification command is a real, copy­able
command rather than a description of one.

**Type consistency:** `Candidate`, `Drop`, and `TopicConfig` are defined
once in Task 1's `agent/sources/base.py` and imported unchanged everywhere
else. `Settings`/`LLMConfig`/`DeliveryConfig` are defined once in Task 1's
`agent/config.py`. `StateEntry` is defined once in Task 3 and never
redefined. `RankedItem` is defined once in Task 5 and consumed as-is by
`digest.build` in Task 6. Function signatures introduced in a task's
"Produces" list match their call sites in every later task verbatim.
