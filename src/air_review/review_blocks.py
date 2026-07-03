"""Shared CodeRabbit-style finding formatters."""

from __future__ import annotations

from typing import Any

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def guess_code_language(file_path: str) -> str:
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


def sort_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda finding: (
            SEVERITY_ORDER.get(finding.get("severity", "info"), 99),
            finding.get("file", ""),
            finding.get("title", ""),
        ),
    )


def format_finding_summary(finding: dict[str, Any], index: int) -> str:
    """Format a numbered PR comment block like CodeRabbit."""
    title = finding.get("title", "Finding").strip()
    severity = finding.get("severity", "info")
    file_path = finding.get("file", "").strip()
    detail = finding.get("detail", "").strip()
    suggestion = finding.get("suggestion", "").strip()
    suggested_code = finding.get("suggested_code", "").strip()

    heading = f"### {index}. {title}"
    if severity in {"critical", "warning"}:
        heading += f" ({severity})"

    lines = [heading, ""]
    if file_path:
        lines.extend([f"`{file_path}`", ""])

    if detail:
        lines.extend([detail, ""])

    if suggested_code:
        language = guess_code_language(file_path)
        lines.extend([f"```{language}", suggested_code, "```"])
    elif suggestion:
        lines.extend([f"**Suggested change:** {suggestion}"])

    return "\n".join(lines).strip()


def format_finding_inline(finding: dict[str, Any]) -> str:
    """Format an inline review comment with GitHub suggestion block."""
    title = finding.get("title", "Finding").strip()
    detail = finding.get("detail", "").strip()
    suggestion = finding.get("suggestion", "").strip()
    suggested_code = finding.get("suggested_code", "").strip()

    lines = [f"**{title}**", ""]
    if detail:
        lines.extend([detail, ""])

    if suggested_code:
        lines.extend(["```suggestion", suggested_code, "```"])
    elif suggestion:
        lines.extend([f"**Suggested change:** {suggestion}"])

    return "\n".join(lines).strip()
