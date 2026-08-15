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
    "You rank candidate links for a research digest against one "
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
