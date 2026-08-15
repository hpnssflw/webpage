"""Entry point: python -m agent --dry-run [--topic SLUG]"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from agent import config, dedupe, date_guard, deliver, digest, events, summarize
from agent.sources import hn
from agent.sources.base import Drop

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
        run_real(args.topic)


if __name__ == "__main__":
    main()
