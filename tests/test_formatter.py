"""Tests for CodeRabbit-style review formatting."""

from air_review.diff_processor import ProcessedDiff
from air_review.formatter import format_review_markdown
from air_review.review_blocks import format_finding_inline, format_finding_summary


def test_format_finding_summary_matches_coderabbit_shape() -> None:
    finding = {
        "severity": "critical",
        "file": "test-ai/demo.py",
        "title": "Handle zero divisor before division (robust)",
        "detail": (
            "The divide helper does not handle b == 0. This will raise ZeroDivisionError "
            "at runtime when the divisor is zero."
        ),
        "suggested_code": (
            "def divide(a, b):\n"
            "    if b == 0:\n"
            "        raise ValueError('Cannot divide by zero')\n"
            "    return a / b"
        ),
        "suggestion": "",
    }

    block = format_finding_summary(finding, 1)

    assert "### 1. Handle zero divisor before division (robust) (critical)" in block
    assert "`test-ai/demo.py`" in block
    assert "ZeroDivisionError" in block
    assert "```python" in block
    assert "raise ValueError" in block


def test_format_finding_inline_uses_github_suggestion_block() -> None:
    finding = {
        "title": "Handle zero divisor before division (robust)",
        "detail": "The divide helper does not handle b == 0.",
        "suggested_code": "if b == 0:\n    raise ValueError('Cannot divide by zero')",
        "suggestion": "",
    }

    block = format_finding_inline(finding)

    assert "**Handle zero divisor before division (robust)**" in block
    assert "```suggestion" in block


def test_format_review_markdown_uses_numbered_code_suggestions() -> None:
    review = {
        "walkthrough": "This PR adds a demo helper and fixes the GitHub review API call.",
        "findings": [
            {
                "category": "bug",
                "severity": "critical",
                "file": "test-ai/demo.py",
                "line_hint": "L2",
                "title": "Handle zero divisor before division (robust)",
                "detail": "The divide helper crashes when b is 0.",
                "suggestion": "",
                "suggested_code": "def divide(a, b):\n    if b == 0:\n        raise ValueError('Cannot divide by zero')\n    return a / b",
            }
        ],
    }
    processed = ProcessedDiff(
        chunks=[],
        reviewed_files=["test-ai/demo.py"],
        skipped_files=[],
        truncated_files=[],
    )

    markdown = format_review_markdown(review, processed, bot_name="CodeGuard")

    assert "## Walkthrough" in markdown
    assert "## Code suggestions" in markdown
    assert "### 1. Handle zero divisor before division (robust) (critical)" in markdown
    assert "Review by CodeGuard" in markdown
    assert "## Action items" not in markdown
    assert "### Summary" not in markdown
