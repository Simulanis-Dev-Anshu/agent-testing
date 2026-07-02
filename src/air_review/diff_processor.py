"""Filter and chunk PR diffs before sending to Gemini."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field

from air_review.config import ReviewConfig


@dataclass
class FilePatch:
    filename: str
    status: str
    patch: str
    additions: int = 0
    deletions: int = 0


@dataclass
class DiffChunk:
    files: list[FilePatch] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(len(file.patch.encode("utf-8")) for file in self.files)

    def to_text(self) -> str:
        sections: list[str] = []
        for file in self.files:
            sections.append(f"--- FILE: {file.filename} ({file.status}) ---")
            sections.append(file.patch)
            sections.append("")
        return "\n".join(sections).strip()


@dataclass
class ProcessedDiff:
    chunks: list[DiffChunk]
    reviewed_files: list[str]
    skipped_files: list[str]
    truncated_files: list[str]

    @property
    def partial_review(self) -> bool:
        return bool(self.skipped_files or self.truncated_files)


def _matches_ignore_pattern(filename: str, patterns: list[str]) -> bool:
    normalized = filename.replace("\\", "/")
    for pattern in patterns:
        if fnmatch.fnmatch(normalized, pattern):
            return True
        if fnmatch.fnmatch(normalized.split("/")[-1], pattern):
            return True
    return False


def filter_files(
    files: list[FilePatch],
    config: ReviewConfig,
) -> tuple[list[FilePatch], list[str]]:
    """Return reviewable files and skipped filenames."""
    reviewable: list[FilePatch] = []
    skipped: list[str] = []

    for file in files:
        if _matches_ignore_pattern(file.filename, config.ignore_patterns):
            skipped.append(file.filename)
            continue
        if not file.patch:
            skipped.append(file.filename)
            continue
        reviewable.append(file)

    return reviewable, skipped


def apply_file_cap(
    files: list[FilePatch],
    max_files: int,
) -> tuple[list[FilePatch], list[str]]:
    if len(files) <= max_files:
        return files, []
    return files[:max_files], [file.filename for file in files[max_files:]]


def apply_byte_cap(
    files: list[FilePatch],
    max_patch_bytes: int,
) -> tuple[list[FilePatch], list[str]]:
    selected: list[FilePatch] = []
    truncated: list[str] = []
    total = 0

    for file in files:
        patch_bytes = len(file.patch.encode("utf-8"))
        if selected and total + patch_bytes > max_patch_bytes:
            truncated.extend([file.filename for file in files[len(selected) :]])
            break
        selected.append(file)
        total += patch_bytes

    return selected, truncated


def chunk_files(
    files: list[FilePatch],
    chunk_patch_bytes: int,
) -> list[DiffChunk]:
    if not files:
        return []

    chunks: list[DiffChunk] = []
    current = DiffChunk()
    current_bytes = 0

    for file in files:
        patch_bytes = len(file.patch.encode("utf-8"))
        if current.files and current_bytes + patch_bytes > chunk_patch_bytes:
            chunks.append(current)
            current = DiffChunk()
            current_bytes = 0

        current.files.append(file)
        current_bytes += patch_bytes

    if current.files:
        chunks.append(current)

    return chunks


def process_diff(
    files: list[FilePatch],
    config: ReviewConfig,
) -> ProcessedDiff:
    """Filter, cap, and chunk file patches for model review."""
    reviewable, ignored = filter_files(files, config)
    capped, overflow = apply_file_cap(reviewable, config.max_files)
    selected, truncated = apply_byte_cap(capped, config.max_patch_bytes)
    chunks = chunk_files(selected, config.chunk_patch_bytes)

    skipped = ignored + overflow
    return ProcessedDiff(
        chunks=chunks,
        reviewed_files=[file.filename for file in selected],
        skipped_files=skipped,
        truncated_files=truncated,
    )


def parse_line_number(line_hint: str | None) -> int | None:
    """Extract a line number from hints like 'L42' or 'line 42'."""
    if not line_hint:
        return None
    match = re.search(r"\d+", line_hint)
    if not match:
        return None
    return int(match.group())
