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
