"""Tests for diff filtering and chunking."""

from air_review.config import ReviewConfig
from air_review.diff_processor import (
    DiffChunk,
    FilePatch,
    apply_byte_cap,
    apply_file_cap,
    chunk_files,
    filter_files,
    process_diff,
)


def _patch(size: int, char: str = "x") -> str:
    return char * size


def test_filter_files_ignores_lockfiles() -> None:
    config = ReviewConfig(ignore_patterns=["package-lock.json"])
    files = [
        FilePatch("src/app.py", "modified", "+print('hi')"),
        FilePatch("package-lock.json", "modified", "+{}"),
    ]
    reviewable, skipped = filter_files(files, config)
    assert [file.filename for file in reviewable] == ["src/app.py"]
    assert skipped == ["package-lock.json"]


def test_filter_files_skips_missing_patch() -> None:
    config = ReviewConfig()
    files = [FilePatch("README.md", "modified", "")]
    reviewable, skipped = filter_files(files, config)
    assert reviewable == []
    assert skipped == ["README.md"]


def test_apply_file_cap() -> None:
    files = [
        FilePatch(f"file{i}.py", "modified", "+x")
        for i in range(5)
    ]
    selected, overflow = apply_file_cap(files, max_files=3)
    assert len(selected) == 3
    assert overflow == ["file3.py", "file4.py"]


def test_apply_byte_cap() -> None:
    files = [
        FilePatch("a.py", "modified", _patch(100)),
        FilePatch("b.py", "modified", _patch(100)),
        FilePatch("c.py", "modified", _patch(100)),
    ]
    selected, truncated = apply_byte_cap(files, max_patch_bytes=150)
    assert [file.filename for file in selected] == ["a.py"]
    assert truncated == ["b.py", "c.py"]


def test_chunk_files_splits_on_byte_budget() -> None:
    files = [
        FilePatch("a.py", "modified", _patch(30_000)),
        FilePatch("b.py", "modified", _patch(30_000)),
        FilePatch("c.py", "modified", _patch(10_000)),
    ]
    chunks = chunk_files(files, chunk_patch_bytes=50_000)
    assert len(chunks) == 2
    assert [file.filename for file in chunks[0].files] == ["a.py"]
    assert [file.filename for file in chunks[1].files] == ["b.py", "c.py"]


def test_process_diff_marks_partial_review() -> None:
    config = ReviewConfig(
        max_files=1,
        max_patch_bytes=50,
        chunk_patch_bytes=50,
        ignore_patterns=["dist/**"],
    )
    files = [
        FilePatch("src/main.py", "modified", _patch(20)),
        FilePatch("src/util.py", "modified", _patch(20)),
        FilePatch("dist/bundle.js", "modified", _patch(20)),
    ]
    processed = process_diff(files, config)
    assert processed.reviewed_files == ["src/main.py"]
    assert "src/util.py" in processed.skipped_files
    assert "dist/bundle.js" in processed.skipped_files
    assert processed.partial_review is True
    assert isinstance(processed.chunks[0], DiffChunk)
