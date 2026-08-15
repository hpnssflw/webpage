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
