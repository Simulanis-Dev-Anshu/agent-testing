"""Prompt templates and response schema for Gemini reviews."""

from __future__ import annotations

REVIEW_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "walkthrough": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "bug",
                            "security",
                            "performance",
                            "quality",
                            "edge_case",
                        ],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["info", "warning", "critical"],
                    },
                    "file": {"type": "string"},
                    "line_hint": {"type": "string"},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "suggested_code": {"type": "string"},
                },
                "required": [
                    "category",
                    "severity",
                    "file",
                    "line_hint",
                    "title",
                    "detail",
                    "suggestion",
                    "suggested_code",
                ],
            },
        },
    },
    "required": ["walkthrough", "findings"],
}


SYSTEM_PROMPT = """You are a senior software engineer writing a pull request review similar to CodeRabbit.

Write like a helpful teammate, not a formal audit report.

Output style:
- walkthrough: 2-4 sentences explaining what the PR changes and the main impact. No headings inside this field.
- findings: actionable issues only, grouped mentally by file. Skip nitpicks (missing newline, formatting-only issues).
- For each finding, include suggested_code with a focused code snippet when a concrete fix exists; otherwise use an empty string and put guidance in suggestion.

Prioritize:
- Correctness bugs and logic errors
- Security issues (injection, auth gaps, secret exposure)
- Missing error handling and edge cases
- Performance hotspots
- Redundant or harmful patterns

Rules:
- Base findings only on the provided diff context.
- Cite exact file paths from the diff headers.
- Use line_hint like "L42" when inferable from diff hunks; otherwise use an empty string.
- Keep titles short and direct.
- Return JSON matching the schema exactly.
"""


def build_chunk_prompt(
    pr_title: str,
    pr_body: str,
    chunk_text: str,
    chunk_index: int,
    chunk_total: int,
) -> str:
    body = pr_body.strip() if pr_body else "(no description provided)"
    return f"""Review this pull request diff chunk.

PR title: {pr_title}
PR description:
{body}

Chunk: {chunk_index + 1} of {chunk_total}

Diff:
{chunk_text}
"""


MERGE_SYSTEM_PROMPT = """You merge multiple chunk-level code review results into one final CodeRabbit-style review.

Rules:
- Deduplicate overlapping findings.
- Keep the highest severity when duplicates conflict.
- Produce one cohesive walkthrough for the entire PR.
- Return JSON matching the schema exactly.
"""


def build_merge_prompt(chunk_reviews: list[dict]) -> str:
    import json

    serialized = json.dumps(chunk_reviews, indent=2)
    return f"""Merge these chunk review JSON objects into one final review:

{serialized}
"""
