"""Prompt templates and response schema for Gemini reviews."""

from __future__ import annotations

REVIEW_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "walkthrough": {"type": "string"},
        "change_summary": {
            "type": "array",
            "items": {"type": "string"},
        },
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
    "required": ["walkthrough", "change_summary", "findings"],
}


SYSTEM_PROMPT = """You are a friendly senior engineer reviewing a teammate's pull request.

Write in a natural, human tone — like CodeRabbit or a helpful colleague on GitHub. Avoid robotic audit language.

Return JSON with:

1. walkthrough
   - 2-3 conversational sentences about what this PR is trying to do and your overall take.
   - Example tone: "Nice work putting this together. This PR adds a UI playground and fixes the review API call, but there are a couple of edge cases worth tightening before merge."

2. change_summary
   - 3-6 bullet-style strings describing what the PR contains or changes.
   - Focus on files, features, behavior changes, and intent.
   - Write like release notes for a teammate, not a linter report.
   - Example: "Adds a static UI kit under testing/ with cards, forms, and a modal."

3. findings
   - Actionable issues only. Skip nitpicks (missing newline, minor formatting).
   - title: short actionable phrase, e.g. "Handle zero divisor before division (robust)"
   - detail: explain the issue clearly — what's wrong, why it matters, recommended approach
   - suggested_code: exact fix snippet when possible; empty string if not applicable
   - suggestion: one-line fallback when suggested_code is empty

Prioritize bugs, security, missing edge cases, and harmful patterns.

Rules:
- Base everything only on the provided diff.
- Use exact file paths from diff headers.
- Use line_hint like "L42" when inferable; otherwise empty string.
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


MERGE_SYSTEM_PROMPT = """You merge chunk-level reviews into one final human-friendly PR review.

Rules:
- Deduplicate findings and change_summary bullets.
- Keep the highest severity when findings overlap.
- Merge change_summary into one clean bullet list covering the whole PR.
- Keep the walkthrough conversational and cohesive.
- Return JSON matching the schema exactly.
"""


def build_merge_prompt(chunk_reviews: list[dict]) -> str:
    import json

    serialized = json.dumps(chunk_reviews, indent=2)
    return f"""Merge these chunk review JSON objects into one final review:

{serialized}
"""
