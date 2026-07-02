"""GitHub API helpers for fetching PR diffs and posting review comments."""

from __future__ import annotations

import os
from dataclasses import dataclass

from github import Auth, Github
from github.PullRequest import PullRequest
from github.Repository import Repository

from air_review.diff_processor import FilePatch, parse_line_number
from air_review.review_blocks import format_finding_inline


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
    def __init__(
        self,
        token: str | None = None,
        repo: str | None = None,
        bot_name: str = "AIR Review",
        comment_marker: str = "<!-- air-review-bot -->",
    ) -> None:
        auth_token = token or os.environ.get("GITHUB_TOKEN")
        if not auth_token:
            raise ValueError("GITHUB_TOKEN is required")

        repository = repo or os.environ.get("GITHUB_REPOSITORY")
        if not repository:
            raise ValueError("GITHUB_REPOSITORY is required (format: owner/repo)")

        self.bot_name = bot_name
        self.comment_marker = comment_marker
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
        full_body = f"{self.comment_marker}\n{body.strip()}"

        for comment in issue.get_comments():
            if self.comment_marker in (comment.body or ""):
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
            and (finding.get("suggested_code") or finding.get("suggestion"))
        ]
        if not eligible:
            return 0

        comments: list[dict] = []
        for finding in eligible:
            line = parse_line_number(finding.get("line_hint"))
            if line is None:
                continue

            comments.append(
                {
                    "path": finding["file"],
                    "body": format_finding_inline(finding),
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
                body=f"Inline suggestions from {self.bot_name}.",
                event="COMMENT",
                comments=comments,
            )
            return len(comments)
        except Exception as exc:
            print(f"Skipped inline review comments: {exc}")
            return 0

    def close(self) -> None:
        self.github.close()
