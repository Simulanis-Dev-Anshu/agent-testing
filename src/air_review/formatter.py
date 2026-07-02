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
        walkthrough = "Review completed for the changed files in this pull request."

    sections = ["## Walkthrough", "", walkthrough.strip(), ""]

    if processed.partial_review:
        skipped_count = len(processed.skipped_files) + len(processed.truncated_files)
        sections.extend(
            [
                f"> Partial review: {skipped_count} file(s) were skipped due to size or filter limits.",
                "",
            ]
        )

    findings = sort_findings(review.get("findings", []))
    if findings:
        sections.extend(["## Code suggestions", ""])
        for index, finding in enumerate(findings, start=1):
            sections.extend([format_finding_summary(finding, index), "", "---", ""])

    if inline_comment_count:
        sections.extend(
            [
                f"> {inline_comment_count} inline suggestion(s) were added directly on changed lines.",
                "",
            ]
        )

    sections.append("---")
    sections.append(f"*Review by {bot_name} — verify suggestions before merging.*")
    return "\n".join(sections).strip()
