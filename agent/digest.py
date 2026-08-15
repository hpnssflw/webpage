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
