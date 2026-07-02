"""Configuration loading from review_config.yaml and environment variables."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path("review_config.yaml")


@dataclass
class ReviewConfig:
    model: str = "gemini-2.5-pro"
    bot_name: str = "AIR Review"
    bot_id: str = "air-review"
    max_files: int = 40
    max_patch_bytes: int = 120_000
    chunk_patch_bytes: int = 50_000
    ignore_patterns: list[str] = field(default_factory=list)
    skip_labels: list[str] = field(default_factory=lambda: ["no-ai-review"])
    inline_comment_severities: list[str] = field(
        default_factory=lambda: ["critical", "warning"]
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewConfig:
        return cls(
            model=data.get("model", cls.model),
            bot_name=str(data.get("bot_name", cls.bot_name)),
            bot_id=str(data.get("bot_id", cls.bot_id)),
            max_files=int(data.get("max_files", 40)),
            max_patch_bytes=int(data.get("max_patch_bytes", 120_000)),
            chunk_patch_bytes=int(data.get("chunk_patch_bytes", 50_000)),
            ignore_patterns=list(data.get("ignore_patterns", [])),
            skip_labels=list(data.get("skip_labels", ["no-ai-review"])),
            inline_comment_severities=list(
                data.get("inline_comment_severities", ["critical", "warning"])
            ),
        )


def find_config_path(start: Path | None = None) -> Path:
    """Search upward from start for review_config.yaml."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / DEFAULT_CONFIG_PATH.name
        if candidate.is_file():
            return candidate
    return Path.cwd() / DEFAULT_CONFIG_PATH.name


def load_config(config_path: Path | None = None) -> ReviewConfig:
    path = config_path or find_config_path()
    if not path.is_file():
        return ReviewConfig()

    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    config = ReviewConfig.from_dict(data)
    if model_override := os.getenv("AIR_REVIEW_MODEL"):
        config.model = model_override
    if bot_name_override := os.getenv("AIR_REVIEW_BOT_NAME"):
        config.bot_name = bot_name_override
    if bot_id_override := os.getenv("AIR_REVIEW_BOT_ID"):
        config.bot_id = bot_id_override
    return config


def bot_comment_marker(bot_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", bot_id.lower()).strip("-") or "air-review"
    return f"<!-- {slug}-bot -->"


def load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
