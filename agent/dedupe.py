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
