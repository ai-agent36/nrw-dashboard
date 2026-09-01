#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_data.py"
BASELINE = json.loads((ROOT / "data/news.json").read_text(encoding="utf-8"))


class FeedValidationTests(unittest.TestCase):
    def run_validator(self, data: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            delete=False,
        ) as handle:
            json.dump(data, handle, ensure_ascii=False)
            path = Path(handle.name)
        try:
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            path.unlink(missing_ok=True)

    def assert_rejected(self, mutate, expected: str) -> None:
        data = copy.deepcopy(BASELINE)
        mutate(data)
        result = self.run_validator(data)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(expected, result.stdout)
        self.assertIn('"errors":', result.stdout)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_baseline_passes(self) -> None:
        result = self.run_validator(copy.deepcopy(BASELINE))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('"errors": 0', result.stdout)

    def test_missing_polling_required_field_is_rejected(self) -> None:
        self.assert_rejected(
            lambda data: data["polling"].pop("sampleSize"),
            "polling: missing sampleSize",
        )

    def test_dangerous_criticism_url_is_rejected(self) -> None:
        self.assert_rejected(
            lambda data: data["governmentCriticism"]["items"][0].update(
                sourceUrl="javascript:alert(1)"
            ),
            "invalid sourceUrl",
        )

    def test_data_post_url_is_rejected(self) -> None:
        self.assert_rejected(
            lambda data: data["socialRadar"]["tiktok"]["posts"][0].update(
                url="data:text/html,<script>alert(1)</script>"
            ),
            "invalid url",
        )

    def test_bad_polling_date_is_rejected(self) -> None:
        self.assert_rejected(
            lambda data: data["polling"].update(publishedAt="28. Juni irgendwann"),
            "polling: invalid publishedAt",
        )

    def test_wrong_social_aggregate_is_rejected(self) -> None:
        self.assert_rejected(
            lambda data: data["socialRadar"]["tiktok"].update(viewsTotal=1),
            "viewsTotal=1, calculated=",
        )

    def test_missing_social_profile_field_is_rejected(self) -> None:
        self.assert_rejected(
            lambda data: data["socialRadar"]["profiles"][1].pop("note"),
            "missing note",
        )

    def test_source_count_mismatch_is_rejected(self) -> None:
        self.assert_rejected(
            lambda data: data["meta"].update(sourceCount=999),
            "sourceCount=999, calculated=",
        )

    def test_renderer_containers_must_be_arrays(self) -> None:
        for field, bad_value in (
            ("signals", "not-an-array"),
            ("ticker", {}),
            ("focusTopics", "not-an-array"),
        ):
            with self.subTest(field=field):
                self.assert_rejected(
                    lambda data, field=field, bad_value=bad_value: data.__setitem__(
                        field, bad_value
                    ),
                    f"{field}: expected array",
                )

    def test_non_object_party_is_rejected_without_traceback(self) -> None:
        self.assert_rejected(
            lambda data: data["polling"]["parties"].__setitem__(0, "bad-party"),
            "polling/party[0]: expected object",
        )

    def test_non_object_post_is_rejected_without_traceback(self) -> None:
        self.assert_rejected(
            lambda data: data["socialRadar"]["tiktok"]["posts"].__setitem__(
                0, "bad-post"
            ),
            "socialRadar/post[0]: expected object",
        )

    def test_non_string_story_id_is_rejected_without_traceback(self) -> None:
        self.assert_rejected(
            lambda data: data["stories"][0].update(id=23),
            "id must be a non-empty string",
        )

    def test_default_port_alias_does_not_inflate_source_count(self) -> None:
        def duplicate_poll_url(data: dict) -> None:
            data["polling"]["methodologyUrl"] = data["polling"]["sourceUrl"].replace(
                "https://www1.wdr.de", "https://www1.wdr.de:443"
            )

        self.assert_rejected(duplicate_poll_url, "sourceCount=36, calculated=35")

    def test_attribution_targets_must_differ(self) -> None:
        self.assert_rejected(
            lambda data: data["lead"].update(
                imageLicenseUrl=data["lead"]["imageSourceUrl"]
            ),
            "imageSourceUrl and imageLicenseUrl must differ",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
