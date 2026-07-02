"""Prompt templates and response schema for Gemini reviews."""

from __future__ import annotations

REVIEW_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
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
                    "line_hint": {"type": "string", "nullable": True},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": [
                    "category",
                    "severity",
                    "file",
                    "title",
                    "detail",
                    "suggestion",
                ],
            },
        },
        "positives": {"type": "array", "items": {"type": "string"}},
        "test_suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "risk_level", "findings", "positives", "test_suggestions"],
}


SYSTEM_PROMPT = """You are a senior software engineer performing a pre-human code review.

Your job is to catch meaningful issues before human reviewers focus on architecture and business logic.

Prioritize:
- Correctness bugs and logic errors
- Security issues (injection, auth gaps, secret exposure, unsafe deserialization)
- Concurrency and race conditions
- Missing error handling and edge cases
- Performance hotspots and unnecessary work
- API contract breaks and backward compatibility risks

Avoid nitpicks about naming or formatting unless they hide real bugs.

Rules:
- Base findings only on the provided diff context.
- Cite file paths from the diff headers.
- Use line_hint like "L42" when you can infer it from diff hunk headers; use null when unknown.
- Be constructive and specific in suggestions.
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


MERGE_SYSTEM_PROMPT = """You merge multiple chunk-level code review results into one final review.

Rules:
- Deduplicate overlapping findings.
- Keep the highest severity when duplicates conflict.
- Produce one cohesive summary for the entire PR.
- Return JSON matching the schema exactly.
"""


def build_merge_prompt(chunk_reviews: list[dict]) -> str:
    import json

    serialized = json.dumps(chunk_reviews, indent=2)
    return f"""Merge these chunk review JSON objects into one final review:

{serialized}
"""
