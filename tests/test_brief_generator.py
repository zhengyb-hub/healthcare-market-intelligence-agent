import json
import unittest
from types import SimpleNamespace

import pandas as pd

from brief_generator import (
    REPORT_SECTIONS,
    build_ai_prompt,
    generate_ai_brief_sections,
    validate_competitor_data,
)


class FakeResponses:
    def __init__(self, output_text):
        self.output_text = output_text
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        return SimpleNamespace(output_text=self.output_text)


class FakeClient:
    def __init__(self, output_text):
        self.responses = FakeResponses(output_text)


def valid_frame():
    return pd.DataFrame(
        [
            {
                "competitor": "Alpha",
                "date": "2026-07-01",
                "source": "Sample Portfolio Data",
                "title": "Creator campaign",
                "content": "Alpha worked with creators to explain a new feature.",
                "category": "Content Strategy",
            },
            {
                "competitor": "Beta",
                "date": "2026-07-02",
                "source": "Sample Portfolio Data",
                "title": "Trust message",
                "content": "Beta emphasized transparent editorial standards.",
                "category": "Brand Positioning",
            },
        ]
    )


class BriefGeneratorTests(unittest.TestCase):
    def test_validation_normalizes_and_sorts_rows(self):
        result = validate_competitor_data(valid_frame())
        self.assertEqual(result.iloc[0]["competitor"], "Beta")
        self.assertEqual(result.iloc[0]["date"], "2026-07-02")

    def test_validation_rejects_missing_columns(self):
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            validate_competitor_data(pd.DataFrame({"competitor": ["Alpha"]}))

    def test_prompt_contains_grounding_contract(self):
        prompt = build_ai_prompt(valid_frame(), "Target", "News", "English")
        self.assertIn("Use only the supplied evidence", prompt)
        self.assertIn("Target", prompt)
        self.assertIn("Creator campaign", prompt)

    def test_ai_generation_uses_responses_api_and_parses_sections(self):
        expected = {section: f"{section} content" for section in REPORT_SECTIONS}
        client = FakeClient(json.dumps(expected))
        result = generate_ai_brief_sections(
            data=valid_frame(),
            brand_name="Target",
            industry="News",
            output_language="English",
            api_key="test-key",
            model="gpt-5.6",
            client=client,
        )
        self.assertEqual(result, expected)
        self.assertEqual(client.responses.last_request["model"], "gpt-5.6")
        self.assertIn("responses", type(client.responses).__name__.lower())

    def test_ai_generation_rejects_incomplete_output(self):
        client = FakeClient(json.dumps({"Executive Summary": "Only one section"}))
        with self.assertRaisesRegex(ValueError, "missing sections"):
            generate_ai_brief_sections(
                valid_frame(),
                "Target",
                "News",
                "English",
                "test-key",
                client=client,
            )


if __name__ == "__main__":
    unittest.main()
