"""Format AI review output for GitHub pull request comments."""

from __future__ import annotations

from typing import Any

from air_review.diff_processor import ProcessedDiff
from air_review.review_blocks import format_finding_summary, sort_findings


def format_review_markdown(
    review: dict[str, Any],
    processed: ProcessedDiff,
    bot_name: str = "AIR Review",
    inline_comment_count: int = 0,
) -> str:
    walkthrough = review.get("walkthrough") or review.get("summary", "")
    if not walkthrough:
        walkthrough = "I reviewed the changes in this PR — here's what stood out."

    change_summary = review.get("change_summary", [])
    findings = sort_findings(review.get("findings", []))

    sections = ["## Walkthrough", "", walkthrough.strip(), ""]

    if processed.partial_review:
        skipped_count = len(processed.skipped_files) + len(processed.truncated_files)
        sections.extend(
            [
                f"> Heads up: this was a partial review — {skipped_count} file(s) were skipped due to size or filter limits.",
                "",
            ]
        )

    if findings:
        sections.extend(["## Code suggestions", ""])
        for index, finding in enumerate(findings, start=1):
            sections.extend([format_finding_summary(finding, index), "", "---", ""])

    if change_summary:
        sections.extend(["## What this PR contains", ""])
        sections.extend(f"- {item.strip()}" for item in change_summary if item.strip())
        sections.append("")

    if inline_comment_count:
        sections.extend(
            [
                f"> I also left {inline_comment_count} inline suggestion(s) directly on the changed lines.",
                "",
            ]
        )

    sections.append("---")
    sections.append(f"*Review by {bot_name} — please double-check before merging.*")
    return "\n".join(sections).strip()
