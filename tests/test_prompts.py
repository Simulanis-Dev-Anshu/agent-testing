"""Tests for Gemini response schema compatibility."""

from google.genai import types

from air_review.prompts import REVIEW_RESPONSE_SCHEMA


def test_review_response_schema_is_valid_for_gemini() -> None:
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=REVIEW_RESPONSE_SCHEMA,
    )
    assert "walkthrough" in config.response_schema["properties"]
    assert "change_summary" in config.response_schema["properties"]
    line_hint = (
        config.response_schema["properties"]["findings"]["items"]["properties"]["line_hint"]
    )
    assert line_hint == {"type": "string"}


def test_review_response_schema_converts_to_gemini_schema() -> None:
    schema = types.Schema.from_json_schema(
        json_schema=types.JSONSchema(**REVIEW_RESPONSE_SCHEMA)
    )
    finding_schema = schema.properties["findings"].items.properties["line_hint"]
    assert finding_schema.type == types.Type.STRING
    assert finding_schema.nullable is not True
