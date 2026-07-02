"""Tests for human-friendly review formatting."""

from air_review.diff_processor import ProcessedDiff
from air_review.formatter import format_review_markdown


def test_format_review_includes_walkthrough_suggestions_and_change_summary() -> None:
    review = {
        "walkthrough": (
            "Nice work on this one. You added a UI playground and wired up basic interactions, "
            "but I'd tighten a couple of edge cases before merge."
        ),
        "change_summary": [
            "Adds a static UI kit under testing/ with cards, alerts, and a modal.",
            "Introduces styles.css for the dark theme component library.",
            "Adds app.js for tabs, modal open/close, and form submit handling.",
        ],
        "findings": [
            {
                "severity": "warning",
                "file": "testing/app.js",
                "title": "Reset modal state after close (robust)",
                "detail": "Closing the modal hides it visually but doesn't reset form values.",
                "suggestion": "Clear inputs when the modal closes.",
                "suggested_code": "",
            }
        ],
    }
    processed = ProcessedDiff(
        chunks=[],
        reviewed_files=["testing/index.html", "testing/app.js"],
        skipped_files=[],
        truncated_files=[],
    )

    markdown = format_review_markdown(review, processed, bot_name="AIR Review")

    assert "## Walkthrough" in markdown
    assert "Nice work on this one." in markdown
    assert "## Code suggestions" in markdown
    assert "## What this PR contains" in markdown
    assert "- Adds a static UI kit under testing/" in markdown
    assert markdown.index("## Code suggestions") < markdown.index("## What this PR contains")
    assert "Review by AIR Review" in markdown
    assert "Model:" not in markdown
