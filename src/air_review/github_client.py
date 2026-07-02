"""GitHub API helpers for fetching PR diffs and posting review comments."""

from __future__ import annotations

import os
from dataclasses import dataclass

from github import Auth, Github
from github.PullRequest import PullRequest
from github.Repository import Repository

from air_review.diff_processor import FilePatch, parse_line_number

BOT_COMMENT_MARKER = "<!-- air-review-bot -->"


def _format_inline_comment(finding: dict) -> str:
    severity = finding.get("severity", "info").title()
    title = finding.get("title", "Finding")
    detail = finding.get("detail", "").strip()
    suggestion = finding.get("suggestion", "").strip()
    suggested_code = finding.get("suggested_code", "").strip()

    lines = [f"**{severity} — {title}**", ""]
    if detail:
        lines.extend([detail, ""])

    if suggested_code:
        lines.extend(["Suggested change:", "", "```suggestion", suggested_code, "```"])
    elif suggestion:
        lines.extend([f"**Fix:** {suggestion}"])

    return "\n".join(lines).strip()


@dataclass
class PullRequestContext:
    number: int
    title: str
    body: str
    author: str
    labels: list[str]
    head_sha: str
    base_sha: str


class GitHubReviewClient:
    def __init__(self, token: str | None = None, repo: str | None = None) -> None:
        auth_token = token or os.environ.get("GITHUB_TOKEN")
        if not auth_token:
            raise ValueError("GITHUB_TOKEN is required")

        repository = repo or os.environ.get("GITHUB_REPOSITORY")
        if not repository:
            raise ValueError("GITHUB_REPOSITORY is required (format: owner/repo)")

        self.github = Github(auth=Auth.Token(auth_token))
        self.repo_name = repository
        self.repo: Repository = self.github.get_repo(repository)

    def get_pull_request(self, pr_number: int) -> PullRequest:
        return self.repo.get_pull(pr_number)

    def fetch_pr_context(self, pr_number: int) -> PullRequestContext:
        pull = self.get_pull_request(pr_number)
        return PullRequestContext(
            number=pull.number,
            title=pull.title or "",
            body=pull.body or "",
            author=pull.user.login if pull.user else "unknown",
            labels=[label.name for label in pull.labels],
            head_sha=pull.head.sha,
            base_sha=pull.base.sha,
        )

    def fetch_file_patches(self, pr_number: int) -> list[FilePatch]:
        pull = self.get_pull_request(pr_number)
        files = pull.get_files()
        patches: list[FilePatch] = []
        for file in files:
            patches.append(
                FilePatch(
                    filename=file.filename,
                    status=file.status,
                    patch=file.patch or "",
                    additions=file.additions,
                    deletions=file.deletions,
                )
            )
        return patches

    def upsert_review_comment(self, pr_number: int, body: str) -> None:
        issue = self.repo.get_issue(pr_number)
        marker = BOT_COMMENT_MARKER
        full_body = f"{marker}\n{body.strip()}"

        for comment in issue.get_comments():
            if marker in (comment.body or ""):
                comment.edit(full_body)
                return

        issue.create_comment(full_body)

    def post_inline_review_comments(
        self,
        pr_number: int,
        head_sha: str,
        findings: list[dict],
        severities: list[str],
    ) -> int:
        """Post inline PR review comments for findings with resolvable line numbers."""
        eligible = [
            finding
            for finding in findings
            if finding.get("severity") in severities
            and finding.get("file")
            and finding.get("suggestion")
        ]
        if not eligible:
            return 0

        comments: list[dict] = []
        for finding in eligible:
            line = parse_line_number(finding.get("line_hint"))
            if line is None:
                continue

            body = _format_inline_comment(finding)
            comments.append(
                {
                    "path": finding["file"],
                    "body": body,
                    "line": line,
                    "side": "RIGHT",
                }
            )

        if not comments:
            return 0

        pull = self.get_pull_request(pr_number)
        try:
            commit = self.repo.get_commit(head_sha)
            pull.create_review(
                commit=commit,
                body="Inline suggestions from AI code review.",
                event="COMMENT",
                comments=comments,
            )
            return len(comments)
        except Exception as exc:
            # Inline comments can fail on API differences, outdated lines, or diff types.
            print(f"Skipped inline review comments: {exc}")
            return 0

    def close(self) -> None:
        self.github.close()
