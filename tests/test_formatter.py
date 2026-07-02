"""Tests for CodeRabbit-style review formatting."""

from air_review.diff_processor import ProcessedDiff
from air_review.formatter import format_review_markdown


def test_format_review_markdown_uses_walkthrough_and_file_sections() -> None:
    review = {
        "walkthrough": "This PR adds a demo helper and fixes the GitHub review API call.",
        "findings": [
            {
                "category": "bug",
                "severity": "critical",
                "file": "test-ai/demo.py",
                "line_hint": "L2",
                "title": "Division by zero",
                "detail": "The divide helper crashes when b is 0.",
                "suggestion": "Guard against zero before dividing.",
                "suggested_code": "def divide(a, b):\n    if b == 0:\n        raise ValueError('Cannot divide by zero')\n    return a / b",
            }
        ],
    }
    processed = ProcessedDiff(chunks=[], reviewed_files=["test-ai/demo.py"], skipped_files=[], truncated_files=[])

    markdown = format_review_markdown(review, processed)

    assert "## Walkthrough" in markdown
    assert "This PR adds a demo helper" in markdown
    assert "### `test-ai/demo.py`" in markdown
    assert "**Critical — Division by zero**" in markdown
    assert "```python" in markdown
    assert "## Action items" in markdown
    assert "Model:" not in markdown
    assert "Files reviewed:" not in markdown
    assert "### Summary" not in markdown
    assert "### What looks good" not in markdown
