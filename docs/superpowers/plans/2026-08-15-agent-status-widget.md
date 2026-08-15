# Agent Status Widget + Public Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the research agent running on the public site — a compact
terminal-styled widget on the homepage and a full live dashboard on
`researcher/agent.html` — fed by a GitHub Actions run every 4 hours that
commits an aggregate `status.json` to a dedicated `agent-data` branch.

**Architecture:** `agent/main.py`'s `run_real` gains a pending-email queue
(new `agent/pending.py`) so collection/ranking can run 4x more often than
delivery, plus a terminal `"run"/"complete"` event. A new pure function in
`agent/status_export.py` turns a run's JSONL event log into `status.json` —
never touching `TopicConfig`, so source config can't leak into it. A GitHub
Actions workflow runs the agent on a cron schedule and pushes the three
data files (`state.json`, `pending.json`, `status.json`) to an orphan
`agent-data` branch. A single vanilla-JS file, fetched by both site pages,
renders whichever mount point (`#agent-widget` or `#agent-dashboard`) is
present on the page.

**Tech Stack:** Python 3.12 stdlib (agent side, no new dependencies),
vanilla JS + inline CSS additions to the existing `styles.css` (site side,
no framework, no build step), GitHub Actions (`ubuntu-latest`, ordinary
YAML, no third-party actions beyond `actions/checkout` and
`actions/setup-python`).

## Global Constraints

- **Cadence:** collection/ranking every 4 hours (`0 */4 * * *`); email
  delivery decoupled, default `email_cadence_hours: 24`. (Spec §
  Scheduling, § Email delivery decoupling.)
- **Stale threshold:** widget dot flips lime→red when `now - updated_at >
  2 × cadence_hours`. (Spec § Homepage widget.)
- **`agent-data` is an orphan branch** with no shared history with
  `main`; `main` is never touched by automated commits. (Spec §
  Scheduling & data architecture.)
- **Redaction by construction:** `status_export.build_status` never
  receives a `TopicConfig` — only a `dict[str, str]` of slug→display-name.
  No function in this plan may widen that signature to accept topic
  `sources`/`keywords`. (Spec § Redaction.)
- **`agent/pending.json` and `agent/status.json` must be added to
  `.gitignore`** on `main`, alongside the existing `agent/state.json`
  entry, before either file is created locally. (Same rule that already
  governs `state.json`.)
- **No test framework.** Every task's verification is a manual command run
  and a read of its output, consistent with the rest of this repo.
- **Commit only files a task's own section lists.** Never stage
  `.claude/settings.local.json` (repo convention, `CLAUDE.md`).
- **This spec supersedes** the Windows-Task-Scheduler scheduling decision
  and the "weekly cadence unchanged" out-of-scope note in
  `2026-08-12-research-agent-design.md`, and the build-time-snapshot public
  replay mechanism in `2026-08-12-run-panel-design.md`. Do not "fix" this
  plan to match those older documents — they are the ones now stale.

---

## Task 1: Make the remote public + orphan `agent-data` branch

**Files:**
- None created or modified in this repo's tracked files — this task is
  entirely `git`/`gh` operations against GitHub.

**Interfaces:**
- Consumes: the `origin` remote (`https://github.com/hpnssflw/webpage.git`,
  already added) and local branch `main` (already renamed from `master`).
- Produces: `hpnssflw/webpage` flipped from private to public, `main`
  pushed, and an orphan branch `agent-data` pushed to the same remote,
  containing a single `README.md`. Later tasks (4, 5) derive the repo
  slug via `git remote get-url origin` — no task hardcodes it.

**Already done, confirmed with the user, do not redo:** `origin` is set to
`https://github.com/hpnssflw/webpage.git`; the local branch is already
`main` (renamed from `master`); the repo is currently **private** and
needs to become **public** — required because `raw.githubusercontent.com`
only serves unauthenticated requests for public repos, and the whole
point of `status.json` is that the site's client-side `fetch()` can read
it with no token. The user explicitly chose "make webpage itself public"
over the alternative of a separate dedicated public repo — do not revisit
that decision.

- [ ] **Step 1: Confirm `gh` is authenticated as `hpnssflw`**

Run:

```powershell
gh auth status
```

The first push attempt (before this task started) failed with
"Repository not found" while `gh` was authenticated as a different
account (`toomuchisnotenough`) — this repo is private, so that account
couldn't see it. If the active account still isn't `hpnssflw`, stop and
ask the user to run `! gh auth switch` (or `! gh auth login`) themselves
before continuing — this tool cannot drive an interactive login prompt.

- [ ] **Step 2: Make the repository public**

Confirm with the user immediately before running this — flipping a
private repo public is the one truly irreversible-in-spirit step in this
task (anyone can see the full history from this point on, including
commits made before this task).

```powershell
gh repo edit hpnssflw/webpage --visibility public --accept-visibility-change-consequences
```

- [ ] **Step 3: Push `main`**

```powershell
git push -u origin main
```

Expected: push succeeds (it previously failed only because the repo
wasn't reachable/public yet under the active account).

- [ ] **Step 4: Create the `agent-data` orphan branch without checking it out locally**

This uses git plumbing so the current working directory (which has
uncommitted-to-`agent-data` site files all over it) is never touched.

```powershell
$readme = "Agent run data -- machine-generated by .github/workflows/agent-run.yml. Do not hand-edit. See docs/superpowers/specs/2026-08-15-agent-status-widget-design.md.`n"
$readme | Out-File -Encoding utf8 -NoNewline "$env:TEMP\agent-data-readme.md"
$blob = git hash-object -w "$env:TEMP\agent-data-readme.md"
$tree = "100644 blob $blob`tREADME.md" | git mktree
$commit = git commit-tree $tree -m "Initialize agent-data branch"
git branch agent-data $commit
git push origin agent-data
Remove-Item "$env:TEMP\agent-data-readme.md"
```

Expected: no errors; `git branch -a` locally shows `agent-data` alongside
`main` (as a local ref pointing at the commit just made — this is fine,
it is never checked out).

- [ ] **Step 5: Verify both branches exist on the remote**

Run:

```powershell
git ls-remote origin
```

Expected: two refs listed, `refs/heads/main` and `refs/heads/agent-data`.

- [ ] **Step 6: Add repo secrets for the workflow (Task 4 will use these)**

Already confirmed with the user — proceed without asking again. This
reads a real API key out of `agent/.env`.

```powershell
gh secret set DEEPSEEK_API_KEY --body (Select-String -Path agent/.env -Pattern '^DEEPSEEK_API_KEY=' | ForEach-Object { $_.Line.Split('=', 2)[1] })
```

SMTP secrets (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`) are
**not** set here — per `PROGRESS.md`, those aren't in `agent/.env` yet
either. Set them the same way, once they exist, before Task 4's workflow
is expected to successfully email anything. Until then the workflow will
run collection/ranking/status-export successfully and skip/retry delivery
(Task 2's try/except around `deliver.send` handles this without crashing
the run).

- [ ] **Step 7: No commit for this task**

Nothing in the local working tree changed — Steps 1–6 only touched
GitHub-side state. Skip straight to confirming Task 2 with the user.

---

## Task 2: Pending-email queue + decoupled delivery cadence

**Files:**
- Create: `agent/pending.py`
- Modify: `agent/dedupe.py` (`mark_sent` → `mark_sent_url`)
- Modify: `agent/digest.py` (build from `PendingItem`, drop "weekly" wording)
- Modify: `agent/summarize.py` (drop "weekly" wording in `RANK_SYSTEM_PROMPT`)
- Modify: `agent/config.py` (`DeliveryConfig` gains `email_cadence_hours`)
- Modify: `agent/defaults.yaml` (add `email_cadence_hours: 24` under `delivery`)
- Modify: `agent/main.py` (`run_real` rewritten around the pending queue)
- Modify: `.gitignore` (add `agent/pending.json`)

**Interfaces:**
- Consumes: `Candidate`, `Drop` (existing `sources/base.py`);
  `RankedItem` (existing `summarize.py`); `StateEntry`, `load_state`,
  `save_state`, `record_seen`, `filter_seen` (existing `dedupe.py`);
  `EventWriter` (existing `events.py`).
- Produces:
  - `agent.pending.PendingItem` — dataclass: `url: str`, `title: str`,
    `source: str`, `topic: str`, `topic_name: str`, `summary: str`,
    `score: int`, `pending_since: str` (ISO 8601, when this item first
    entered the queue)
  - `agent.pending.PendingQueue` — dataclass: `last_email_at: str | None`,
    `items: list[PendingItem]`
  - `agent.pending.load_pending(path: Path) -> PendingQueue`
  - `agent.pending.save_pending(path: Path, queue: PendingQueue) -> None`
  - `agent.pending.add_kept(queue: PendingQueue, topic_name: str, ranked: list[RankedItem], now: datetime) -> None`
  - `agent.pending.filter_already_pending(candidates: list[Candidate], queue: PendingQueue) -> tuple[list[Candidate], list[Drop]]`
    — drops candidates already sitting in the queue (reason `"seen"`,
    `detail={"pending_since": ...}`), so an item waiting out the email
    cadence isn't re-sent to DeepSeek for ranking on every subsequent 4h
    cycle. Must run after `dedupe.filter_seen` and before
    `summarize.rank_topic` for each topic.
  - `agent.pending.is_email_due(queue: PendingQueue, now: datetime, cadence_hours: int) -> bool`
  - `agent.pending.group_by_topic(queue: PendingQueue) -> dict[str, list[PendingItem]]`
  - `agent.dedupe.mark_sent_url(state: dict[str, StateEntry], url: str) -> None` (replaces `mark_sent(state, candidate)`)
  - `agent.digest.build(items_by_topic: dict[str, list[PendingItem]]) -> tuple[str, str]` (signature changed: `PendingItem`, not `RankedItem`)
  - `agent.config.DeliveryConfig.email_cadence_hours: int` (new field)

- [ ] **Step 1: Write `agent/pending.py`**

```python
"""Pending-email queue: items ranked above threshold that haven't been
emailed yet, plus when the last email actually went out. Exists because
collection/ranking now run every 4 hours but email delivery stays on a
coarser cadence — see docs/superpowers/specs/2026-08-15-agent-status-widget-design.md
§ Email delivery decoupling."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from agent.sources.base import Candidate, Drop
from agent.summarize import RankedItem


@dataclass
class PendingItem:
    url: str
    title: str
    source: str
    topic: str
    topic_name: str
    summary: str
    score: int
    pending_since: str  # ISO 8601 -- when this item first entered the queue


@dataclass
class PendingQueue:
    last_email_at: str | None  # ISO 8601, None if never emailed
    items: list[PendingItem]


def load_pending(path: Path) -> PendingQueue:
    if not path.exists():
        return PendingQueue(last_email_at=None, items=[])
    raw = json.loads(path.read_text(encoding="utf-8"))
    return PendingQueue(
        last_email_at=raw.get("last_email_at"),
        items=[PendingItem(**item) for item in raw.get("items", [])],
    )


def save_pending(path: Path, queue: PendingQueue) -> None:
    raw = {
        "last_email_at": queue.last_email_at,
        "items": [asdict(item) for item in queue.items],
    }
    path.write_text(json.dumps(raw, indent=2, sort_keys=True), encoding="utf-8")


def add_kept(queue: PendingQueue, topic_name: str, ranked: list[RankedItem], now: datetime) -> None:
    for item in ranked:
        queue.items.append(
            PendingItem(
                url=item.candidate.url,
                title=item.candidate.title,
                source=item.candidate.source,
                topic=item.candidate.topic,
                topic_name=topic_name,
                summary=item.summary,
                score=item.score,
                pending_since=now.isoformat(),
            )
        )


def filter_already_pending(candidates: list[Candidate], queue: PendingQueue) -> tuple[list[Candidate], list[Drop]]:
    """Drop candidates already sitting in the queue, awaiting the email
    cadence. Without this, an item that survived ranking once but hasn't
    been emailed yet (times_sent still 0, so dedupe.filter_seen lets it
    through) gets re-collected and re-sent to DeepSeek for ranking on
    every subsequent 4h cycle until the email gate finally fires."""
    pending_since_by_url = {item.url: item.pending_since for item in queue.items}
    kept: list[Candidate] = []
    drops: list[Drop] = []
    for candidate in candidates:
        since = pending_since_by_url.get(candidate.url)
        if since is not None:
            drops.append(
                Drop(url=candidate.url, title=candidate.title, reason="seen", detail={"pending_since": since})
            )
        else:
            kept.append(candidate)
    return kept, drops


def is_email_due(queue: PendingQueue, now: datetime, cadence_hours: int) -> bool:
    if not queue.items:
        return False
    if queue.last_email_at is None:
        return True
    last = datetime.fromisoformat(queue.last_email_at)
    return (now - last).total_seconds() >= cadence_hours * 3600


def group_by_topic(queue: PendingQueue) -> dict[str, list[PendingItem]]:
    grouped: dict[str, list[PendingItem]] = {}
    for item in queue.items:
        grouped.setdefault(item.topic_name, []).append(item)
    for items in grouped.values():
        items.sort(key=lambda i: i.score, reverse=True)
    return grouped
```

- [ ] **Step 2: Verify `pending.py` with synthetic data (no network)**

Run:

```powershell
python -c '
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from agent import pending
from agent.summarize import RankedItem
from agent.sources.base import Candidate

now = datetime(2026, 8, 15, 14, 0, tzinfo=timezone.utc)
c = Candidate(url="https://a", title="a", source="hn", topic="ai-agents", published_at=now, score=100, excerpt=None)
ranked = [RankedItem(candidate=c, summary="s", score=9)]

q = pending.PendingQueue(last_email_at=None, items=[])
assert pending.is_email_due(q, now, 24) is False, "empty queue must never be due"
pending.add_kept(q, "AI Agents & Engineering", ranked, now)
assert pending.is_email_due(q, now, 24) is True, "never-emailed queue with items must be due"
assert q.items[0].pending_since == now.isoformat(), q.items[0]

# a candidate already sitting in the queue must not be sent to ranking again
c2 = Candidate(url="https://a", title="a (recollected)", source="hn", topic="ai-agents", published_at=now, score=105, excerpt=None)
c3 = Candidate(url="https://z", title="new one", source="hn", topic="ai-agents", published_at=now, score=50, excerpt=None)
still_new, seen_drops = pending.filter_already_pending([c2, c3], q)
assert still_new == [c3], still_new
assert len(seen_drops) == 1 and seen_drops[0].reason == "seen" and seen_drops[0].detail == {"pending_since": now.isoformat()}, seen_drops

q.last_email_at = (now - timedelta(hours=1)).isoformat()
assert pending.is_email_due(q, now, 24) is False, "1h ago must not be due at 24h cadence"
q.last_email_at = (now - timedelta(hours=25)).isoformat()
assert pending.is_email_due(q, now, 24) is True, "25h ago must be due at 24h cadence"

grouped = pending.group_by_topic(q)
assert list(grouped.keys()) == ["AI Agents & Engineering"], grouped

tmp = Path(tempfile.mktemp(suffix=".json"))
pending.save_pending(tmp, q)
reloaded = pending.load_pending(tmp)
assert reloaded.items[0].url == "https://a" and reloaded.last_email_at == q.last_email_at
tmp.unlink()
print("pending OK")
'
```

Expected: `pending OK`.

- [ ] **Step 3: Change `mark_sent` to `mark_sent_url` in `agent/dedupe.py`**

Replace:

```python
def mark_sent(state: dict[str, StateEntry], candidate: Candidate) -> None:
    """Called once a candidate has actually been delivered. Requires
    record_seen to have already run for this candidate in the same run —
    a KeyError here means the pipeline sent something it never recorded,
    which is a bug worth surfacing loudly rather than papering over."""
    state[url_hash(candidate.url)].times_sent += 1
```

with:

```python
def mark_sent_url(state: dict[str, StateEntry], url: str) -> None:
    """Called once an item has actually been delivered. Requires
    record_seen to have already run for this URL in some prior run — a
    KeyError here means the pipeline sent something it never recorded,
    which is a bug worth surfacing loudly rather than papering over.
    Takes a bare URL (not a Candidate) because the pending queue stores
    items as flat PendingItem records, not Candidates."""
    state[url_hash(url)].times_sent += 1
```

- [ ] **Step 4: Verify `mark_sent_url` with synthetic data (no network)**

Run:

```powershell
python -c '
from datetime import datetime, timezone
from agent import dedupe
now = datetime(2026, 8, 15, tzinfo=timezone.utc)
state = {dedupe.url_hash("https://a"): dedupe.StateEntry(first_seen=now.isoformat(), last_score=50, times_sent=0)}
dedupe.mark_sent_url(state, "https://a")
assert state[dedupe.url_hash("https://a")].times_sent == 1
print("mark_sent_url OK")
'
```

Expected: `mark_sent_url OK`.

- [ ] **Step 5: Rewrite `agent/digest.py`**

```python
"""Assemble the pending-email queue into a digest email body."""

from __future__ import annotations

from agent.pending import PendingItem


def build(items_by_topic: dict[str, list[PendingItem]]) -> tuple[str, str]:
    """Return (subject, plain-text body)."""
    lines = ["Research digest", ""]
    total = 0
    for topic_name, items in items_by_topic.items():
        if not items:
            continue
        lines.append(topic_name)
        lines.append("-" * len(topic_name))
        for item in items:
            lines.append(f"- {item.title}")
            lines.append(f"  {item.summary}")
            lines.append(f"  {item.url}")
            total += 1
        lines.append("")

    subject = f"Research digest — {total} items" if total else "Research digest — nothing new"
    return subject, "\n".join(lines)
```

- [ ] **Step 6: Verify digest assembly against `PendingItem` (no network)**

Run:

```powershell
python -c '
from agent.digest import build
from agent.pending import PendingItem

item = PendingItem(url="https://example.com/a", title="Example", source="hn", topic="ai-agents", topic_name="AI Agents & Engineering", summary="A one-line summary.", score=8)
subject, body = build({"AI Agents & Engineering": [item]})
assert "1 items" in subject
assert "Example" in body and "A one-line summary." in body and item.url in body
assert "weekly" not in subject.lower() and "weekly" not in body.lower()
print(subject)
print("digest OK")
'
```

Expected: the subject line and `digest OK`.

- [ ] **Step 7: Reword `RANK_SYSTEM_PROMPT` in `agent/summarize.py`**

Replace:

```python
RANK_SYSTEM_PROMPT = (
    "You rank candidate links for a weekly research digest against one "
    "topic. For each candidate, judge relevance to the topic on a 1-10 "
```

with:

```python
RANK_SYSTEM_PROMPT = (
    "You rank candidate links for a research digest against one "
    "topic. For each candidate, judge relevance to the topic on a 1-10 "
```

- [ ] **Step 8: Add `email_cadence_hours` to `agent/config.py`**

Replace:

```python
@dataclass(frozen=True)
class DeliveryConfig:
    to: str
    from_: str
```

with:

```python
@dataclass(frozen=True)
class DeliveryConfig:
    to: str
    from_: str
    email_cadence_hours: int
```

And replace:

```python
    return Settings(
        llm=LLMConfig(base_url=llm_raw["base_url"], model=llm_raw["model"]),
        delivery=DeliveryConfig(to=delivery_raw["to"], from_=delivery_raw["from"]),
    )
```

with:

```python
    return Settings(
        llm=LLMConfig(base_url=llm_raw["base_url"], model=llm_raw["model"]),
        delivery=DeliveryConfig(
            to=delivery_raw["to"],
            from_=delivery_raw["from"],
            email_cadence_hours=delivery_raw["email_cadence_hours"],
        ),
    )
```

- [ ] **Step 9: Add `email_cadence_hours` to `agent/defaults.yaml`**

Replace:

```yaml
delivery:
  to: hypnosisflow@gmail.com
  from: agent@localhost
```

with:

```yaml
delivery:
  to: hypnosisflow@gmail.com
  from: agent@localhost
  email_cadence_hours: 24 # digest rollup cadence; collection/ranking run every 4h regardless
```

- [ ] **Step 10: Verify config loads the new field**

Run:

```powershell
python -c 'from pathlib import Path; from agent import config; s = config.load_settings(Path("agent/defaults.yaml")); assert s.delivery.email_cadence_hours == 24, s; print("config OK", s)'
```

Expected: `config OK Settings(...)`.

- [ ] **Step 11: Add `agent/pending.json` to `.gitignore`**

Replace:

```
agent/.env
agent/state.json
agent/runs/
```

with:

```
agent/.env
agent/state.json
agent/pending.json
agent/runs/
```

- [ ] **Step 12: Rewrite `run_real` in `agent/main.py`**

Replace the imports:

```python
from agent import config, dedupe, date_guard, deliver, digest, events, summarize
from agent.sources import hn
from agent.sources.base import Drop
```

with:

```python
from agent import config, dedupe, date_guard, deliver, digest, events, pending, summarize
from agent.sources import hn
from agent.sources.base import Drop
```

Add, near the other path constants:

```python
PENDING_PATH = AGENT_DIR / "pending.json"
```

Replace the entire `run_real` function body with:

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
    queue = pending.load_pending(PENDING_PATH)

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

        kept, drops = pending.filter_already_pending(kept, queue)
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

        for item in keep:
            writer.emit(
                "rank",
                "kept",
                topic=topic.slug,
                source=item.candidate.source,
                url=item.candidate.url,
                title=item.candidate.title,
                score=item.score,
            )

        pending.add_kept(queue, topic.name, keep, now)

    emailed = False
    if pending.is_email_due(queue, now, settings.delivery.email_cadence_hours):
        grouped = pending.group_by_topic(queue)
        subject, body = digest.build(grouped)
        try:
            deliver.send(subject, body, settings)
        except Exception as exc:  # noqa: BLE001 — delivery must never crash a scheduled run; retried once due again next time
            writer.emit("deliver", "failed", detail={"error": str(exc), "items": len(queue.items)})
            print(f"Email delivery failed, will retry next run: {exc}")
        else:
            for item in queue.items:
                dedupe.mark_sent_url(state, item.url)
            total_items = len(queue.items)
            writer.emit("deliver", "sent", detail={"items": total_items, "topics": len(grouped)})
            queue.items = []
            queue.last_email_at = now.isoformat()
            emailed = True
            print(f"Sent {total_items} items across {len(grouped)} topics.")
    else:
        print(f"Nothing emailed this run. Pending queue: {len(queue.items)} item(s).")

    dedupe.save_state(STATE_PATH, state)
    pending.save_pending(PENDING_PATH, queue)
    writer.emit("run", "complete", detail={"emailed": emailed, "pending_total": len(queue.items)})
    writer.close()
    print(f"Run recorded: {writer.path}")
```

- [ ] **Step 13: Verify `run_real` still runs end to end**

This requires `DEEPSEEK_API_KEY` (already in `agent/.env` per `PROGRESS.md`)
but not SMTP credentials — the try/except means a missing SMTP config
fails the delivery step gracefully rather than crashing the run. Confirm
with the user before running, since it makes a real DeepSeek call.

```powershell
python -m agent --topic ai-agents
```

Expected: either `Sent N items...` (if SMTP happens to be configured) or
`Email delivery failed, will retry next run: ...` followed by
`Nothing emailed this run` being skipped (since the try/except path
prints its own message) — either way, no traceback, and a final
`Run recorded: ...jsonl` line. Then confirm `agent/pending.json` exists
and contains today's kept items (if any survived ranking) with
`git status` showing it as untracked (gitignored, not staged).

- [ ] **Step 14: Commit**

```powershell
git add agent/pending.py agent/dedupe.py agent/digest.py agent/summarize.py agent/config.py agent/defaults.yaml agent/main.py .gitignore
git commit -m "Decouple email delivery from collection/ranking cadence via a pending queue"
```

---

## Task 3: `status_export.py` — build the public status aggregate

**Files:**
- Create: `agent/status_export.py`
- Modify: `agent/main.py` (`run_real` writes `agent/status.json` at the end)
- Modify: `.gitignore` (add `agent/status.json`)

**Interfaces:**
- Consumes: JSONL event dicts as produced by `agent.events.read_events`
  (Task 4/existing); `agent.pending.PendingQueue` (Task 2).
- Produces:
  - `agent.status_export.build_status(run_events: list[dict], topic_names: dict[str, str], queue: PendingQueue, email_cadence_hours: int, cadence_hours: int, previous_status: dict | None, now: datetime) -> dict`

**A note on the redaction constraint:** this function's signature takes
`topic_names: dict[str, str]`, never `TopicConfig`. Do not change this
signature to accept `TopicConfig`, `list[TopicConfig]`, or anything that
exposes `.sources`/`.keywords` — that is what makes the redaction property
in the spec true by construction rather than by discipline.

- [ ] **Step 1: Write `agent/status_export.py`**

```python
"""Builds agent/status.json -- the public aggregate the site's widget
fetches -- from a run's JSONL event log, the pending-email queue, and the
previous status.json's run history.

Deliberately never reads TopicConfig: this module's only entry point
accepts a plain dict[str, str] of slug -> display name, so topic source
config (keywords, subreddits, feed URLs, search queries) has no path into
the output. See docs/superpowers/specs/2026-08-15-agent-status-widget-design.md
§ Redaction."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from agent.pending import PendingQueue

RECENT_EVENTS_LIMIT = 15
RUN_HISTORY_LIMIT = 24


def build_status(
    run_events: list[dict[str, Any]],
    topic_names: dict[str, str],
    queue: PendingQueue,
    email_cadence_hours: int,
    cadence_hours: int,
    previous_status: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    funnel: dict[str, dict[str, int]] = {
        slug: {"collected": 0, "in_window": 0, "new": 0, "kept": 0} for slug in topic_names
    }
    recent_events: list[dict[str, Any]] = []
    dropped_by_stage: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for event in run_events:
        topic = event.get("topic")
        if topic not in funnel:
            continue
        stage = event.get("stage")
        kind = event.get("event")

        if stage == "collect" and kind == "candidate":
            funnel[topic]["collected"] += 1
        elif kind == "drop":
            dropped_by_stage[topic][stage] += 1
            recent_events.append(
                {
                    "ts": event["ts"],
                    "verdict": "drop",
                    "topic": topic,
                    "title": event.get("title", ""),
                    "reason": event.get("reason", ""),
                }
            )
        elif stage == "rank" and kind == "kept":
            funnel[topic]["kept"] += 1
            recent_events.append(
                {
                    "ts": event["ts"],
                    "verdict": "kept",
                    "source": event.get("source", ""),
                    "topic": topic,
                    "title": event.get("title", ""),
                    "score": event.get("score"),
                }
            )

    for slug, counts in funnel.items():
        collected = counts["collected"]
        counts["in_window"] = collected - dropped_by_stage[slug].get("date_guard", 0)
        counts["new"] = counts["in_window"] - dropped_by_stage[slug].get("dedupe", 0)

    recent_events.sort(key=lambda e: e["ts"], reverse=True)
    recent_events = recent_events[:RECENT_EVENTS_LIMIT]

    completed = any(e.get("stage") == "run" and e.get("event") == "complete" for e in run_events)
    prev_streak = (previous_status or {}).get("streak", 0)
    streak = prev_streak + 1 if completed else 0

    prev_history = (previous_status or {}).get("run_history", [])
    this_run_kept = sum(counts["kept"] for counts in funnel.values())
    run_history = (prev_history + [{"ts": now.isoformat(), "kept": this_run_kept}])[-RUN_HISTORY_LIMIT:]

    return {
        "updated_at": now.isoformat(),
        "cadence_hours": cadence_hours,
        "streak": streak,
        "last_email_at": queue.last_email_at,
        "email_cadence_hours": email_cadence_hours,
        "pending_email_count": len(queue.items),
        "topics": [
            {"slug": slug, "name": topic_names[slug], "collected": c["collected"], "kept": c["kept"]}
            for slug, c in funnel.items()
        ],
        "funnel": funnel,
        "recent_events": recent_events,
        "run_history": run_history,
    }
```

- [ ] **Step 2: Verify `build_status` against synthetic events (no network)**

Run:

```powershell
python -c '
from datetime import datetime, timezone
from agent.status_export import build_status
from agent.pending import PendingQueue

now = datetime(2026, 8, 15, 14, 0, tzinfo=timezone.utc)
events = [
    {"ts": "2026-08-15T14:00:00+00:00", "stage": "collect", "event": "candidate", "topic": "ai-agents", "url": "https://a", "title": "A"},
    {"ts": "2026-08-15T14:00:00+00:00", "stage": "collect", "event": "candidate", "topic": "ai-agents", "url": "https://b", "title": "B"},
    {"ts": "2026-08-15T14:00:01+00:00", "stage": "date_guard", "event": "drop", "topic": "ai-agents", "url": "https://b", "title": "B", "reason": "outside_window"},
    {"ts": "2026-08-15T14:00:02+00:00", "stage": "rank", "event": "kept", "topic": "ai-agents", "source": "hn", "url": "https://a", "title": "A", "score": 9},
    {"ts": "2026-08-15T14:00:03+00:00", "stage": "run", "event": "complete", "detail": {"emailed": False, "pending_total": 1}},
]
queue = PendingQueue(last_email_at=None, items=[])
status = build_status(events, {"ai-agents": "AI Agents & Engineering"}, queue, 24, 4, None, now)

assert status["funnel"]["ai-agents"] == {"collected": 2, "in_window": 1, "new": 1, "kept": 1}, status["funnel"]
assert status["streak"] == 1, status["streak"]
assert status["topics"] == [{"slug": "ai-agents", "name": "AI Agents & Engineering", "collected": 2, "kept": 1}], status["topics"]
assert len(status["recent_events"]) == 2, status["recent_events"]
assert status["recent_events"][0]["verdict"] in ("kept", "drop")
assert status["run_history"][-1] == {"ts": now.isoformat(), "kept": 1}, status["run_history"]

# a run missing the terminal "run"/"complete" event resets streak to 0
status2 = build_status(events[:-1], {"ai-agents": "AI Agents & Engineering"}, queue, 24, 4, status, now)
assert status2["streak"] == 0, status2["streak"]
assert status2["run_history"] == status["run_history"] + [{"ts": now.isoformat(), "kept": 1}]

print("status_export OK")
'
```

Expected: `status_export OK`.

- [ ] **Step 3: Wire `status_export` into `run_real`**

In `agent/main.py`, add to the imports:

```python
import json

from agent import config, dedupe, date_guard, deliver, digest, events, pending, status_export, summarize
```

Add near the other path constants:

```python
STATUS_PATH = AGENT_DIR / "status.json"
```

At the end of `run_real`, replace:

```python
    dedupe.save_state(STATE_PATH, state)
    pending.save_pending(PENDING_PATH, queue)
    writer.emit("run", "complete", detail={"emailed": emailed, "pending_total": len(queue.items)})
    writer.close()
    print(f"Run recorded: {writer.path}")
```

with:

```python
    dedupe.save_state(STATE_PATH, state)
    pending.save_pending(PENDING_PATH, queue)
    writer.emit("run", "complete", detail={"emailed": emailed, "pending_total": len(queue.items)})
    writer.close()

    all_topics = config.load_topics(TOPICS_DIR, DEFAULTS_PATH)
    topic_names = {t.slug: t.name for t in all_topics}
    previous_status = json.loads(STATUS_PATH.read_text(encoding="utf-8")) if STATUS_PATH.exists() else None
    run_events = events.read_events(writer.path)
    status = status_export.build_status(
        run_events, topic_names, queue, settings.delivery.email_cadence_hours, 4, previous_status, now
    )
    STATUS_PATH.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Run recorded: {writer.path}")
    print(f"Status written: {STATUS_PATH}")
```

`config.load_topics` is called again here (rather than reusing the
possibly-`--topic`-filtered `topics` variable from earlier in the
function) deliberately: `status.json`'s `topics` field always covers all
three topics, even on a manually filtered debug run. A filtered run's
`funnel`/`recent_events` will only have data for the run topic(s) actually
processed — the other topics simply show zero for this run, which is
correct (they weren't touched) though it means a single filtered real run
temporarily understates the other topics' `run_history` entry. This is a
known, accepted limitation of manual `--topic` runs; the production
GitHub Actions workflow (Task 4) never filters, so it never hits this
case. The `4` passed as `cadence_hours` is hardcoded rather than read from
config because cadence is a property of the GitHub Actions schedule
(Task 4), not something `defaults.yaml` tracks — if that ever changes,
this literal is the one place to update.

- [ ] **Step 4: Add `agent/status.json` to `.gitignore`**

Replace:

```
agent/.env
agent/state.json
agent/pending.json
agent/runs/
```

with:

```
agent/.env
agent/state.json
agent/pending.json
agent/status.json
agent/runs/
```

- [ ] **Step 5: Verify the full wiring with a real (or dry) run**

Run:

```powershell
python -m agent --dry-run --topic ai-agents
```

`--dry-run` does not call `run_real`, so this only confirms Tasks 1–3
haven't broken the existing dry-run path. Then, confirming with the user
first (this makes a real DeepSeek call, same as Task 2 Step 13):

```powershell
python -m agent --topic ai-agents
python -c 'import json; from pathlib import Path; status = json.loads(Path("agent/status.json").read_text()); assert "updated_at" in status and "funnel" in status and "topics" in status; print("status.json keys:", sorted(status.keys())); print("streak:", status["streak"])'
```

Expected: `--dry-run` runs cleanly as before; the real run produces
`agent/status.json`, and the follow-up command prints its keys and a
`streak` of `1` (or higher, if this is not the first real run since this
task shipped).

- [ ] **Step 6: Commit**

```powershell
git add agent/status_export.py agent/main.py .gitignore
git commit -m "Add status_export.py and wire it into run_real"
```

---

## Task 4: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/agent-run.yml`

**Interfaces:**
- Consumes: `agent/requirements.txt` (existing); the `origin` remote and
  `agent-data` branch (Task 1); `run_real`'s three output files (Tasks
  2–3); repo secrets `DEEPSEEK_API_KEY` and (once added) `SMTP_HOST`/
  `SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD` (Task 1 Step 6).
- Produces: a scheduled job that updates `agent-data` every 4 hours.

- [ ] **Step 1: Write `.github/workflows/agent-run.yml`**

```yaml
name: Research agent run

on:
  schedule:
    - cron: "0 */4 * * *"
  workflow_dispatch: {}

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: Check out agent code
        uses: actions/checkout@v4
        with:
          ref: main
          path: code

      - name: Check out agent data
        uses: actions/checkout@v4
        with:
          ref: agent-data
          path: data

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r code/agent/requirements.txt

      - name: Move prior state into the code checkout
        run: |
          mkdir -p code/agent
          [ -f data/agent/state.json ] && cp data/agent/state.json code/agent/state.json || true
          [ -f data/agent/pending.json ] && cp data/agent/pending.json code/agent/pending.json || true
          [ -f data/agent/status.json ] && cp data/agent/status.json code/agent/status.json || true

      - name: Run the agent
        working-directory: code
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
        run: python -m agent

      - name: Copy updated state back into the data checkout
        run: |
          mkdir -p data/agent
          cp code/agent/state.json data/agent/state.json
          cp code/agent/pending.json data/agent/pending.json
          cp code/agent/status.json data/agent/status.json

      - name: Commit and push agent-data
        working-directory: data
        run: |
          git config user.name "agent-bot"
          git config user.email "agent-bot@users.noreply.github.com"
          git add agent/state.json agent/pending.json agent/status.json
          git diff --cached --quiet || git commit -m "Update agent status $(date -u +%Y-%m-%dT%H:%MZ)"
          git push
```

- [ ] **Step 2: Confirm the repo slug with the user and note it for Task 5**

Run:

```powershell
git remote get-url origin
```

This prints the `owner/repo` slug Task 1 established. Task 5's
`STATUS_URL` constant must use this exact value — copy it down now so
Task 5 doesn't have to re-derive it.

- [ ] **Step 3: Verify with a manual dispatch run**

Confirm with the user first — this is a real, live run against paid APIs,
triggered on GitHub's infrastructure rather than locally.

```powershell
git add .github/workflows/agent-run.yml
git commit -m "Add scheduled GitHub Actions workflow for the research agent"
git push
gh workflow run "Research agent run"
```

Then poll until it finishes:

```powershell
gh run list --workflow="Research agent run" --limit 1
```

Once the run shows `completed`/`success` (or `completed`/`failure` — check
which before assuming success), fetch its log and confirm no traceback:

```powershell
gh run view --log $(gh run list --workflow="Research agent run" --limit 1 --json databaseId --jq '.[0].databaseId')
```

Expected: the log shows `Run recorded: ...` and `Status written: ...`
lines with no Python traceback. Then confirm the branch actually updated:

```powershell
git fetch origin agent-data
git show origin/agent-data:agent/status.json
```

Expected: valid JSON matching the schema from Task 3's verification step.

**Note:** this step pushes the workflow file to `main` (a normal,
non-bot commit — allowed) before triggering it, since GitHub Actions can
only run workflows that already exist on the target ref.

- [ ] **Step 4: Commit**

(Already committed and pushed as part of Step 3, since the workflow had
to exist on `main` before it could be dispatched. No separate commit
step here — if Step 3's push hasn't happened yet for any reason, run:)

```powershell
git add .github/workflows/agent-run.yml
git commit -m "Add scheduled GitHub Actions workflow for the research agent"
```

---

## Task 5: `assets/agent-widget.js`

**Files:**
- Create: `assets/agent-widget.js`

**Interfaces:**
- Consumes: `agent/status.json`'s schema (Task 3), fetched from
  `https://raw.githubusercontent.com/<owner>/<repo>/agent-data/agent/status.json`
  (`<owner>/<repo>` = the slug confirmed in Task 4 Step 2).
- Produces: renders into `#agent-widget` (compact) and/or
  `#agent-dashboard` (full) if present on the page — neither element
  exists yet; Tasks 6 and 7 add them.

- [ ] **Step 1: Write `assets/agent-widget.js`**

Replace `<owner>/<repo>` in `STATUS_URL` below with the value confirmed in
Task 4 Step 2 before saving this file.

```javascript
(function () {
  "use strict";

  var STATUS_URL =
    "https://raw.githubusercontent.com/<owner>/<repo>/agent-data/agent/status.json";

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function fmtCountdown(seconds) {
    if (seconds <= 0) return "due now";
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    var s = Math.floor(seconds % 60);
    return pad(h) + ":" + pad(m) + ":" + pad(s);
  }

  function isStale(status) {
    var updated = new Date(status.updated_at).getTime();
    var staleAfterMs = status.cadence_hours * 2 * 3600 * 1000;
    return Date.now() - updated > staleAfterMs;
  }

  function sparkline(history) {
    var glyphs = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"];
    if (!history.length) return "";
    var max = 1;
    for (var i = 0; i < history.length; i++) {
      if (history[i].kept > max) max = history[i].kept;
    }
    return history
      .map(function (run) {
        if (run.kept === 0) return '<span class="agent-spark-zero">▁</span>';
        var level = Math.min(glyphs.length - 1, Math.round((run.kept / max) * (glyphs.length - 1)));
        return glyphs[level];
      })
      .join("");
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderUnavailable(mount) {
    mount.innerHTML = '<p class="agent-unavailable mono">agent status unavailable</p>';
  }

  function startCountdown(mount, status) {
    var target = mount.querySelector("[data-countdown]");
    if (!target) return;
    var nextRunAt = new Date(status.updated_at).getTime() + status.cadence_hours * 3600 * 1000;
    function tick() {
      var remaining = Math.round((nextRunAt - Date.now()) / 1000);
      target.textContent = "next check " + fmtCountdown(remaining);
    }
    tick();
    setInterval(tick, 1000);
  }

  function renderCompact(mount, status) {
    var stale = isStale(status);
    var dotClass = stale ? "agent-dot-stale" : "agent-dot-online";
    var label = stale ? "stale" : "online";

    var topicsLine = status.topics
      .map(function (t) {
        return (
          escapeHtml(t.name.toLowerCase()) +
          ' <span class="agent-count">' + t.kept + "/" + t.collected + "</span>"
        );
      })
      .join("   ");

    mount.innerHTML =
      '<a class="agent-widget-link" href="researcher/agent.html">' +
      '<span class="' + dotClass + '">●</span> agent ' + label +
      ' <span class="agent-muted">· runs every ' + status.cadence_hours + 'h · streak ' + status.streak + '</span><br>' +
      '<span class="agent-tagline">schema-validated LLM ranking · full audit trail</span><br>' +
      '<span class="agent-spark">' + sparkline(status.run_history) + '</span> <span class="agent-muted">last ' + status.run_history.length + ' runs</span><br>' +
      '<span class="agent-topics">' + topicsLine + '</span><br>' +
      '<span class="agent-muted" data-countdown></span> <span class="agent-arrow">view dashboard →</span>' +
      '</a>';

    startCountdown(mount, status);
  }

  function renderDashboard(mount, status) {
    var stale = isStale(status);
    var dotClass = stale ? "agent-dot-stale" : "agent-dot-online";
    var label = stale ? "stale" : "online";

    var funnelRows = status.topics
      .map(function (t) {
        var f = status.funnel[t.slug];
        return (
          '<div class="agent-funnel-row">' +
          '<span class="agent-funnel-label">' + escapeHtml(t.name.toUpperCase()) + '</span>' +
          '<span class="agent-funnel-counts">collected ' + f.collected +
          ' → in-window ' + f.in_window +
          ' → new ' + f.new +
          ' → kept ' + f.kept + '</span>' +
          '</div>'
        );
      })
      .join("");

    var tickerRows = status.recent_events
      .map(function (e) {
        var verdictClass = e.verdict === "kept" ? "agent-kept" : "agent-drop";
        var verdictLabel = e.verdict === "kept" ? "KEPT" : "DROP";
        var detail = e.verdict === "kept" ? "score " + e.score : e.reason;
        var time = e.ts.slice(11, 19);
        return (
          '<div class="agent-ticker-row">' +
          '<span class="agent-muted">' + time + '</span> ' +
          '<span class="' + verdictClass + '">' + verdictLabel + '</span> ' +
          '<span class="agent-ticker-topic">' + escapeHtml(e.topic) + '</span> ' +
          '<span class="agent-ticker-title">&quot;' + escapeHtml(e.title) + '&quot;</span> ' +
          '<span class="agent-muted">' + escapeHtml(detail) + '</span>' +
          '</div>'
        );
      })
      .join("");

    mount.innerHTML =
      '<div class="agent-dashboard-header">' +
      '<span class="' + dotClass + '">●</span> AGENT ' + label.toUpperCase() +
      ' <span class="agent-muted">runs every ' + status.cadence_hours + 'h · streak ' + status.streak + '</span>' +
      '</div>' +
      '<p class="agent-tagline">Building production AI pipelines: schema-validated LLM calls, automatic fallback, full audit trail of every decision the ranker makes.</p>' +
      '<div class="agent-spark">' + sparkline(status.run_history) + ' <span class="agent-muted">last ' + status.run_history.length + ' runs</span></div>' +
      '<hr class="agent-divider">' +
      '<div class="agent-funnel">' + funnelRows + '</div>' +
      '<hr class="agent-divider">' +
      '<div class="agent-ticker">' + tickerRows + '</div>';

    startCountdown(mount, status);
  }

  function init() {
    var compactMount = document.getElementById("agent-widget");
    var dashboardMount = document.getElementById("agent-dashboard");
    if (!compactMount && !dashboardMount) return;

    fetch(STATUS_URL, { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("status fetch failed: " + res.status);
        return res.json();
      })
      .then(function (status) {
        if (compactMount) renderCompact(compactMount, status);
        if (dashboardMount) renderDashboard(dashboardMount, status);
      })
      .catch(function () {
        if (compactMount) renderUnavailable(compactMount);
        if (dashboardMount) renderUnavailable(dashboardMount);
      });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
```

- [ ] **Step 2: Verify against a local sample `status.json`**

This file is served over `raw.githubusercontent.com` in production, but
`fetch()` has no way to know that at test time — point it at a local file
temporarily to verify rendering without needing Task 4's live branch.

```powershell
mkdir -Force agent-data-sample\agent
```

Write a sample file at `agent-data-sample\agent\status.json`:

```json
{
  "updated_at": "2026-08-15T14:00:03+00:00",
  "cadence_hours": 4,
  "streak": 11,
  "last_email_at": "2026-08-15T09:00:00+00:00",
  "email_cadence_hours": 24,
  "pending_email_count": 7,
  "topics": [
    { "slug": "ai-agents", "name": "AI Agents & Engineering", "collected": 32, "kept": 5 },
    { "slug": "data-viz", "name": "Data Viz", "collected": 18, "kept": 0 },
    { "slug": "full-stack", "name": "Full-Stack Architecture", "collected": 24, "kept": 2 }
  ],
  "funnel": {
    "ai-agents": { "collected": 32, "in_window": 21, "new": 9, "kept": 5 },
    "data-viz": { "collected": 18, "in_window": 13, "new": 4, "kept": 0 },
    "full-stack": { "collected": 24, "in_window": 17, "new": 6, "kept": 2 }
  },
  "recent_events": [
    { "ts": "2026-08-15T14:00:01+00:00", "verdict": "kept", "source": "hn", "topic": "ai-agents", "title": "Production agent evals, one year in", "score": 9 },
    { "ts": "2026-08-15T14:00:01+00:00", "verdict": "drop", "topic": "full-stack", "title": "React 19 notes", "reason": "outside_window" }
  ],
  "run_history": [
    { "ts": "2026-08-15T10:00:02+00:00", "kept": 3 },
    { "ts": "2026-08-15T14:00:03+00:00", "kept": 7 }
  ]
}
```

Then, temporarily edit `assets/agent-widget.js`'s `STATUS_URL` (do not
commit this edit) to `"agent-data-sample/agent/status.json"`, and create a
scratch HTML file `test-widget.html` at the repo root:

```html
<!DOCTYPE html><html><body style="background:#202020;padding:40px">
<div id="agent-widget" style="max-width:500px"></div>
<div id="agent-dashboard" style="max-width:600px;margin-top:40px"></div>
<link rel="stylesheet" href="styles.css">
<script src="assets/agent-widget.js"></script>
</body></html>
```

```powershell
python -m http.server 5678 --bind 127.0.0.1
```

Open `http://127.0.0.1:5678/test-widget.html` in a browser (or `curl` it
and visually inspect the rendered HTML isn't feasible for JS-rendered
content — this one genuinely needs a browser). Confirm: the dot is lime
(not red — `updated_at` in the sample is recent relative to test time,
adjust the sample's timestamp forward if the test runs much later), the
sparkline renders, per-topic counts show, and the countdown ticks. Then
edit the sample's `updated_at` to something 9+ hours in the past, reload,
and confirm the dot turns red and label changes to "stale".

Finally, revert `STATUS_URL` back to the real
`raw.githubusercontent.com/...` value, and delete `test-widget.html` and
`agent-data-sample/` (scratch files, not part of the commit).

- [ ] **Step 3: Commit**

```powershell
git add assets/agent-widget.js
git commit -m "Add the agent status widget's shared fetch/render script"
```

---

## Task 6: Homepage widget

**Files:**
- Modify: `index.html`
- Modify: `styles.css`

**Interfaces:**
- Consumes: `assets/agent-widget.js` (Task 5) via `#agent-widget` mount
  point.

- [ ] **Step 1: Add the mount point to `index.html`**

Replace:

```html
        </li>
      </ul>
    </div>
  </section>

  <section id="lab">
```

with:

```html
        </li>
      </ul>
      <div id="agent-widget"></div>
    </div>
  </section>

  <section id="lab">
```

- [ ] **Step 2: Add the script tag**

Replace:

```html
  <footer>
```

with:

```html
  <script src="assets/agent-widget.js" defer></script>

  <footer>
```

- [ ] **Step 3: Add widget CSS to `styles.css`**

Update the accent comment (this is no longer the only break from the
monochrome palette). Replace:

```css
/* The only accent the monochrome palette allows: the lead-in drops to
   muted, the thesis stays at full strength and turns italic. Contrast of
   value and slope, not of hue. Weight stays light — italic already carries
   the emphasis, and bolding it as well would fight the thin setting. */
.accent {
```

with:

```css
/* One of two deliberate breaks from the otherwise monochrome palette: the
   lead-in drops to muted, the thesis stays at full strength and turns
   italic. Contrast of value and slope, not of hue. Weight stays light —
   italic already carries the emphasis, and bolding it as well would fight
   the thin setting. The other break is the agent status widget's
   lime/red accents, further down this file. */
.accent {
```

Then append, at the end of the file:

```css

/* --- Agent status widget ----------------------------------------
   Terminal aesthetic layered on top of the site's monochrome system —
   the second deliberate palette break, see the .accent comment above.
   Lime = online/kept, red = stale/dropped. .agent-widget is the
   homepage-sized preview; .agent-dashboard (researcher/agent.html) is
   the full view. Both are populated by assets/agent-widget.js. */

:root {
  --agent-bg: #141414;
  --agent-border: #2a2a2a;
  --agent-lime: #7cfc00;
  --agent-red: #ff4d4d;
}

/* The mount points (#agent-widget on the homepage, #agent-dashboard on
   researcher/agent.html) carry only an id in the markup — assets/agent-
   widget.js replaces their innerHTML entirely, so the styled "card" lives
   on .agent-widget-link (homepage: the mount's whole content is one
   <a>) and directly on #agent-dashboard (not a link, so no wrapper
   needed). Do not select `.agent-widget` / `.agent-dashboard` as classes
   — neither element has one. */

#agent-widget {
  margin-top: 28px;
}

.agent-widget-link {
  display: block;
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  line-height: 1.7;
  color: var(--text);
  text-decoration: none;
  background: var(--agent-bg);
  border: 1px solid var(--agent-border);
  border-radius: 4px;
  padding: 14px 16px;
  transition: border-color 0.25s ease, transform 0.25s ease;
}

.agent-widget-link:hover,
.agent-widget-link:focus-visible {
  text-decoration: none;
  border-color: #4d4d4d;
  transform: translateX(2px);
}

.agent-dot-online {
  color: var(--agent-lime);
}

.agent-dot-stale {
  color: var(--agent-red);
}

.agent-muted {
  color: var(--muted);
}

.agent-arrow {
  color: var(--muted);
}

.agent-spark {
  color: var(--agent-lime);
  letter-spacing: 1px;
}

.agent-spark-zero {
  color: var(--agent-red);
}

.agent-count {
  color: var(--agent-lime);
}

.agent-unavailable {
  color: var(--muted);
  margin: 0;
}

.agent-tagline {
  display: block;
  color: var(--muted);
  font-style: italic;
}

#agent-dashboard p.agent-tagline {
  margin: 4px 0 10px;
  max-width: 42em;
}
```

- [ ] **Step 4: Verify visually**

Run:

```powershell
python -m http.server 5678 --bind 127.0.0.1
```

Open `http://127.0.0.1:5678/` in a browser. Before Task 4's workflow has
run at least once, `status.json` won't exist on `agent-data` yet, so
expect the fallback "agent status unavailable" line — that is the correct
behavior to see right now, not a bug. If Task 4 has already run
successfully by this point, confirm the widget renders with real data
instead.

- [ ] **Step 5: Commit**

```powershell
git add index.html styles.css
git commit -m "Add the homepage agent status widget"
```

---

## Task 7: Dashboard section on `researcher/agent.html` + narrative sync

**Files:**
- Modify: `researcher/agent.html`
- Modify: `styles.css`
- Modify: `docs/agent-plan.md`

**Interfaces:**
- Consumes: `assets/agent-widget.js` (Task 5) via `#agent-dashboard` mount
  point.

- [ ] **Step 1: Add the mount point, dashboard-first, to `researcher/agent.html`**

Replace:

```html
      <p class="subtitle">
        A living plan for a background agent that watches data viz,
        full-stack architecture, and AI engineering so research doesn't
        compete with writing time.
      </p>

      <div class="body">
```

with:

```html
      <p class="subtitle">
        A living plan for a background agent that watches data viz,
        full-stack architecture, and AI engineering so research doesn't
        compete with writing time.
      </p>

      <div id="agent-dashboard"></div>

      <div class="body">
```

- [ ] **Step 2: Add the script tag**

Replace:

```html
  <footer>
```

with:

```html
  <script src="../assets/agent-widget.js" defer></script>

  <footer>
```

- [ ] **Step 3: Add dashboard-specific CSS to `styles.css`**

`assets/agent-widget.js`'s `renderDashboard` (Task 5) references classes
that don't exist yet in `styles.css` — `#agent-dashboard` needs its own
card chrome (Task 6 only styled the homepage `.agent-widget-link`), and
the funnel/ticker rows need their own rules. Append, after the block Task
6 added:

```css

#agent-dashboard {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  line-height: 1.7;
  background: var(--agent-bg);
  border: 1px solid var(--agent-border);
  border-radius: 4px;
  padding: 14px 16px;
  margin: 0 0 48px;
}

.agent-divider {
  border: none;
  border-top: 1px solid var(--agent-border);
  margin: 12px 0;
}

.agent-funnel-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.agent-funnel-label {
  color: var(--text-strong);
  min-width: 8em;
}

.agent-funnel-counts {
  color: var(--muted);
}

.agent-ticker-row {
  margin-bottom: 4px;
}

.agent-kept {
  color: var(--agent-lime);
}

.agent-drop {
  color: var(--agent-red);
}

.agent-ticker-topic {
  color: var(--text);
}

.agent-ticker-title {
  color: var(--text-strong);
}
```

- [ ] **Step 4: Sync the narrative's cadence and stack wording**

The page currently says "Once a week" and "Windows Task Scheduler" — both
now inaccurate given this plan's changes. Replace:

```html
        <p>
          The agent's only job is to read so I don't have to read
          everything myself. Once a week it hands me a short, curated
          list of what actually moved in data viz, full-stack
          architecture, and AI engineering — links and a sentence each,
          nothing published, nothing public. Raw material for LAB posts,
          not a LAB post itself.
        </p>
```

with:

```html
        <p>
          The agent's only job is to read so I don't have to read
          everything myself. It checks every few hours; a curated digest
          of what actually moved in data viz, full-stack architecture,
          and AI engineering — links and a sentence each — rolls up once
          a day. Nothing published, nothing public. Raw material for LAB
          posts, not a LAB post itself.
        </p>
```

Replace:

```html
          <li>Windows Task Scheduler for the trigger; SMTP for delivery.</li>
```

with:

```html
          <li>GitHub Actions on a schedule for the trigger; SMTP for delivery, decoupled onto its own coarser cadence so collection can run more often than the inbox needs to hear from it.</li>
```

Replace:

```html
        <h2 id="cadence"><span class="num">05</span>Cadence &amp; format</h2>
        <p>
          Weekly to start — daily would just move the same reading load
          into more, smaller interruptions. Each digest groups items
          under the three topic headers, five to ten per group, one line
          of summary and a link each. Cadence is the first knob to turn
          if the volume feels wrong in either direction.
        </p>
```

with:

```html
        <h2 id="cadence"><span class="num">05</span>Cadence &amp; format</h2>
        <p>
          Collection and ranking run every four hours — frequent enough
          that the live status above reflects what's actually happening
          right now. The email digest stays coarser, rolling up
          everything new once a day, so the inbox doesn't get six emails
          for one afternoon's reading. Each digest groups items under the
          three topic headers, one line of summary and a link each.
        </p>
```

Replace:

```html
        <h2 id="open-questions">What's still open</h2>
        <ul>
          <li>Daily vs weekly — start weekly, watch whether Friday's digest already feels stale by Wednesday.</li>
          <li>Resurfacing — a link dismissed once shouldn't come back next week just because dedupe only tracks URLs verbatim.</li>
          <li>Budget — search and LLM calls both cost money per run; weekly cadence keeps this small, but the number should get watched once it's real.</li>
        </ul>
```

with:

```html
        <h2 id="open-questions">What's still open</h2>
        <ul>
          <li>Whether once-a-day is the right email rollup — watch whether the inbox feels stale or noisy and adjust from there.</li>
          <li>Resurfacing — a link dismissed once shouldn't come back just because dedupe only tracks URLs verbatim.</li>
          <li>Budget — search and LLM calls cost money per run, and collection now runs six times a day instead of once a week; worth watching GitHub Actions minutes and DeepSeek spend as this settles in.</li>
        </ul>
```

Replace:

```html
        <h2 id="status">Status</h2>
        <p>
          Building — the pipeline runs end to end on Hacker News alone: collect,
          filter for recency, dedupe, rank with DeepSeek, assemble, and deliver
          by email. Reddit, RSS, release watching, and web search are next.
        </p>
```

with:

```html
        <h2 id="status">Status</h2>
        <p>
          Running — the pipeline runs end to end on Hacker News alone, on a
          schedule: collect, filter for recency, dedupe, rank with DeepSeek,
          hold in a pending queue, and deliver by email once a day. The live
          status above reflects the actual current state of that schedule.
          Reddit, RSS, release watching, and web search are next.
        </p>
```

- [ ] **Step 5: Sync `docs/agent-plan.md`**

Replace:

```markdown
A background agent that reads so Artem doesn't have to read everything
himself. Once a week it produces a short, curated list of what actually
moved in three topics — links and a one-line summary each. Nothing
published, nothing public. Raw material for his own LAB writing, not a
LAB post itself.
```

with:

```markdown
A background agent that reads so Artem doesn't have to read everything
himself. It checks every 4 hours; a short, curated list of what actually
moved in three topics rolls up into an email once a day — links and a
one-line summary each. Nothing published, nothing public. Raw material
for his own LAB writing, not a LAB post itself.
```

Replace:

```markdown
- Windows Task Scheduler for the trigger (this repo has no GitHub remote); SMTP for delivery.
```

with:

```markdown
- GitHub Actions on a schedule for the trigger (`0 */4 * * *`); SMTP for delivery on its own, coarser cadence — see `docs/superpowers/specs/2026-08-15-agent-status-widget-design.md`.
```

Replace:

```markdown
## Cadence & format

Weekly to start. Each digest groups items under the three topic headers,
five to ten per group, one line of summary and a link each.
```

with:

```markdown
## Cadence & format

Collection and ranking run every 4 hours; email delivery rolls up
everything new once a day (`email_cadence_hours` in `defaults.yaml`).
Each digest groups items under the three topic headers, one line of
summary and a link each.
```

Replace:

```markdown
- Where it runs — resolved: Windows Task Scheduler (this repo has no GitHub remote), secrets in `agent/.env`.
- Budget — search and LLM calls both cost money per run; weekly cadence keeps this small, but watch it once it's real.
```

with:

```markdown
- Where it runs — resolved: GitHub Actions (`.github/workflows/agent-run.yml`), secrets in repo settings; `agent/.env` still used for local `--dry-run`/manual runs.
- Budget — search and LLM calls cost money per run, and collection now runs 6x/day instead of weekly; watch GitHub Actions minutes and DeepSeek spend once this has run for a while.
```

- [ ] **Step 6: Verify visually and check the doc diff**

```powershell
python -m http.server 5678 --bind 127.0.0.1
```

Open `http://127.0.0.1:5678/researcher/agent.html`. Confirm the dashboard
mount appears above the narrative, styled with its own border/background
(Step 3's CSS), and (if Task 4 has run by now) shows real funnel/ticker
data; otherwise the "agent status unavailable" fallback, same as Task 6.
Read through the updated narrative paragraphs for sense — this step is a
manual read, not a scripted check.

- [ ] **Step 7: Commit**

```powershell
git add researcher/agent.html styles.css docs/agent-plan.md
git commit -m "Add live dashboard to researcher/agent.html and sync narrative to the new cadence"
```

---

## Verification summary (spec § Testing / verification coverage)

- `status_export.py` renderer correctness — Task 3 Step 2 (synthetic
  events, funnel math checked by hand-computed expected values).
- Pending-queue / email-gate logic — Task 2 Step 2 (`is_email_due` at
  various ages) and Task 2 Step 13 (one real `run_real` call).
- GitHub Actions workflow — Task 4 Step 3 (manual `workflow_dispatch`,
  log + branch content inspected).
- Widget JS — Task 5 Step 2 (local sample file, both fresh and stale
  timestamps, in an actual browser).
- Fetch failure fallback — implicitly covered by Task 6 Step 4 and Task 7
  Step 5, both run before Task 4's workflow has necessarily produced real
  data yet.
- Visual check by Artem — Task 6 Step 4, Task 7 Step 5.
