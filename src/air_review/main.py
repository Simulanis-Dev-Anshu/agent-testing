"""CLI entry point for the AI code review agent."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from air_review.config import ReviewConfig, load_config, load_dotenv_if_present
from air_review.diff_processor import ProcessedDiff, process_diff
from air_review.gemini_client import GeminiReviewClient
from air_review.github_client import BOT_COMMENT_MARKER, GitHubReviewClient


def should_skip_review(labels: list[str], config: ReviewConfig) -> bool:
    return any(label in config.skip_labels for label in labels)


def format_finding(finding: dict[str, Any]) -> str:
    category = finding.get("category", "review")
    severity = finding.get("severity", "info")
    file_path = finding.get("file", "unknown")
    line_hint = finding.get("line_hint")
    location = f"`{file_path}`"
    if line_hint:
        location += f" ~{line_hint}"
    title = finding.get("title", "Finding")
    detail = finding.get("detail", "").strip()
    suggestion = finding.get("suggestion", "").strip()
    lines = [f"- **[{category}/{severity}]** {location} — **{title}**"]
    if detail:
        lines.append(f"  - {detail}")
    if suggestion:
        lines.append(f"  - **Suggestion:** {suggestion}")
    return "\n".join(lines)


def format_review_markdown(
    review: dict[str, Any],
    processed: ProcessedDiff,
    model: str,
    inline_comment_count: int = 0,
) -> str:
    risk = review.get("risk_level", "low")
    summary = review.get("summary", "No summary provided.")
    findings = review.get("findings", [])
    positives = review.get("positives", [])
    test_suggestions = review.get("test_suggestions", [])

    critical_or_warnings = [
        finding
        for finding in findings
        if finding.get("severity") in {"critical", "warning"}
    ]
    suggestions = [
        finding for finding in findings if finding.get("severity") == "info"
    ]

    sections = [
        "## AI Code Review (Gemini)",
        "",
        (
            f"**Risk:** {risk} | **Files reviewed:** {len(processed.reviewed_files)} "
            f"| **Model:** {model}"
        ),
    ]

    if processed.partial_review:
        skipped_count = len(processed.skipped_files) + len(processed.truncated_files)
        sections.append(
            f"**Note:** Partial review — {skipped_count} file(s) skipped due to filters or size limits."
        )

    if inline_comment_count:
        sections.append(
            f"**Inline comments posted:** {inline_comment_count} suggestion(s) on specific lines."
        )

    sections.extend(["", "### Summary", summary, ""])

    sections.append("### Critical / Warnings")
    if critical_or_warnings:
        sections.extend(format_finding(finding) for finding in critical_or_warnings)
    else:
        sections.append("- No critical or warning-level issues found.")
    sections.append("")

    sections.append("### Suggestions")
    if suggestions:
        sections.extend(format_finding(finding) for finding in suggestions)
    else:
        sections.append("- No additional suggestions.")
    sections.append("")

    sections.append("### What looks good")
    if positives:
        sections.extend(f"- {item}" for item in positives)
    else:
        sections.append("- No specific positives noted.")
    sections.append("")

    sections.append("### Suggested tests")
    if test_suggestions:
        sections.extend(f"- {item}" for item in test_suggestions)
    else:
        sections.append("- No specific test suggestions.")
    sections.append("")
    sections.append(
        "---\n*Automated first-pass review. Human reviewers should focus on architecture and product logic.*"
    )

    return "\n".join(sections)


def parse_event_labels(event_path: str | None) -> list[str]:
    if not event_path or not os.path.isfile(event_path):
        return []
    with open(event_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    pull_request = payload.get("pull_request") or {}
    labels = pull_request.get("labels") or []
    return [label.get("name", "") for label in labels if label.get("name")]


def resolve_pr_number(args: argparse.Namespace) -> int:
    if args.pr is not None:
        return args.pr
    env_pr = os.environ.get("PR_NUMBER")
    if env_pr:
        return int(env_pr)
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and os.path.isfile(event_path):
        with open(event_path, encoding="utf-8") as handle:
            payload = json.load(handle)
        pull_request = payload.get("pull_request") or {}
        number = pull_request.get("number")
        if number is not None:
            return int(number)
    raise ValueError("PR number not provided. Use --pr or set PR_NUMBER / GITHUB_EVENT_PATH.")


def resolve_repo_name(args: argparse.Namespace) -> str | None:
    if args.repo:
        return args.repo
    return os.environ.get("GITHUB_REPOSITORY")


def run_review(args: argparse.Namespace) -> int:
    load_dotenv_if_present()
    config = load_config()
    pr_number = resolve_pr_number(args)
    repo_name = resolve_repo_name(args)

    labels = parse_event_labels(os.environ.get("GITHUB_EVENT_PATH"))
    if should_skip_review(labels, config):
        print(f"Skipping PR #{pr_number}: label in {config.skip_labels}")
        return 0

    github_client = GitHubReviewClient(repo=repo_name)
    try:
        context = github_client.fetch_pr_context(pr_number)
        if should_skip_review(context.labels, config):
            print(f"Skipping PR #{pr_number}: label in {config.skip_labels}")
            return 0

        file_patches = github_client.fetch_file_patches(pr_number)
        processed = process_diff(file_patches, config)

        gemini_client = GeminiReviewClient(model=config.model)
        review = gemini_client.review_diff(
            pr_title=context.title,
            pr_body=context.body,
            processed=processed,
        )

        inline_count = 0
        if not args.no_inline:
            try:
                inline_count = github_client.post_inline_review_comments(
                    pr_number=pr_number,
                    head_sha=context.head_sha,
                    findings=review.get("findings", []),
                    severities=config.inline_comment_severities,
                )
            except Exception as exc:
                print(f"Inline review comments failed, continuing with summary: {exc}")

        markdown = format_review_markdown(
            review=review,
            processed=processed,
            model=config.model,
            inline_comment_count=inline_count,
        )
        github_client.upsert_review_comment(pr_number, markdown)
        print(f"Posted AI review comment on PR #{pr_number}")
        return 0
    finally:
        github_client.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI code review agent for GitHub PRs")
    parser.add_argument("--pr", type=int, help="Pull request number")
    parser.add_argument("--repo", help="Repository in owner/repo format")
    parser.add_argument(
        "--no-inline",
        action="store_true",
        help="Skip posting inline review comments on code lines",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        exit_code = run_review(args)
    except Exception as exc:
        print(f"AI review failed: {exc}", file=sys.stderr)
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
