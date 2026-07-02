"""Gemini API client for structured code reviews."""

from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

from air_review.diff_processor import DiffChunk, ProcessedDiff
from air_review.prompts import (
    MERGE_SYSTEM_PROMPT,
    REVIEW_RESPONSE_SCHEMA,
    SYSTEM_PROMPT,
    build_chunk_prompt,
    build_merge_prompt,
)


class GeminiReviewClient:
    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-pro") -> None:
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY is required")
        self.client = genai.Client(api_key=key)
        self.model = model

    def _generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=REVIEW_RESPONSE_SCHEMA,
                temperature=0.35,
            ),
        )
        text = response.text or "{}"
        return json.loads(text)

    def review_chunk(
        self,
        pr_title: str,
        pr_body: str,
        chunk: DiffChunk,
        chunk_index: int,
        chunk_total: int,
    ) -> dict[str, Any]:
        prompt = build_chunk_prompt(
            pr_title=pr_title,
            pr_body=pr_body,
            chunk_text=chunk.to_text(),
            chunk_index=chunk_index,
            chunk_total=chunk_total,
        )
        return self._generate_json(SYSTEM_PROMPT, prompt)

    def merge_reviews(self, chunk_reviews: list[dict[str, Any]]) -> dict[str, Any]:
        if len(chunk_reviews) == 1:
            return chunk_reviews[0]
        prompt = build_merge_prompt(chunk_reviews)
        return self._generate_json(MERGE_SYSTEM_PROMPT, prompt)

    def review_diff(
        self,
        pr_title: str,
        pr_body: str,
        processed: ProcessedDiff,
    ) -> dict[str, Any]:
        if not processed.chunks:
            return {
                "walkthrough": "I couldn't find reviewable diff content after filtering.",
                "change_summary": [],
                "findings": [],
            }

        chunk_reviews = [
            self.review_chunk(
                pr_title=pr_title,
                pr_body=pr_body,
                chunk=chunk,
                chunk_index=index,
                chunk_total=len(processed.chunks),
            )
            for index, chunk in enumerate(processed.chunks)
        ]
        return self.merge_reviews(chunk_reviews)
