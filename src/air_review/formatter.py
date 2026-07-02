"""Format AI review output for GitHub pull request comments."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from air_review.diff_processor import ProcessedDiff

SEVERITY_LABELS = {
    "critical": "Critical",
    "warning": "Warning",
    "info": "Suggestion",
}


def _format_finding_block(finding: dict[str, Any]) -> list[str]:
    severity = SEVERITY_LABELS.get(finding.get("severity", "info"), "Note")
    title = finding.get("title", "Finding")
    detail = finding.get("detail", "").strip()
    suggestion = finding.get("suggestion", "").strip()
    suggested_code = finding.get("suggested_code", "").strip()

    lines = [f"**{severity} — {title}**", ""]
    if detail:
        lines.extend([detail, ""])

    if suggested_code:
        language = _guess_code_language(finding.get("file", ""))
        lines.extend([f"```{language}", suggested_code, "```", ""])
    elif suggestion:
        lines.extend([f"**Fix:** {suggestion}", ""])

    return lines


def _guess_code_language(file_path: str) -> str:
    if file_path.endswith((".py", ".pyi")):
        return "python"
    if file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
        return "typescript"
    if file_path.endswith((".yml", ".yaml")):
        return "yaml"
    if file_path.endswith(".json"):
        return "json"
    if file_path.endswith((".sh", ".bash")):
        return "bash"
    return ""


def format_review_markdown(
    review: dict[str, Any],
    processed: ProcessedDiff,
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

    findings = review.get("findings", [])
    if findings:
        sections.extend(["## Review", ""])
        findings_by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for finding in findings:
            findings_by_file[finding.get("file", "unknown")].append(finding)

        for file_path in sorted(findings_by_file):
            sections.extend([f"### `{file_path}`", ""])
            for finding in findings_by_file[file_path]:
                sections.extend(_format_finding_block(finding))
            sections.append("---")
            sections.append("")

    action_items = [
        finding
        for finding in findings
        if finding.get("severity") in {"critical", "warning"}
    ]
    if action_items:
        sections.extend(["## Action items", ""])
        for finding in action_items:
            file_path = finding.get("file", "unknown")
            title = finding.get("title", "Address finding")
            sections.append(f"- [ ] {title} (`{file_path}`)")
        sections.append("")

    if inline_comment_count:
        sections.extend(
            [
                f"> {inline_comment_count} inline comment(s) were added on specific lines.",
                "",
            ]
        )

    sections.append("---")
    sections.append("*Automated review — verify suggestions before merging.*")
    return "\n".join(sections).strip()
