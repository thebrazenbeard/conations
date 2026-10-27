"""Adversarial contract tests: Conations history never supplies active drive."""

import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

from conation_history_context import (
    MAX_HISTORICAL_EVENTS,
    HistoricalConationEvidence,
    HistoryContextError,
    historical_context,
    parse_history_export,
)
from conation_manifest import build_manifest


class HistoryContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        event_dir = self.root / "events" / "2026-09-04"
        event_dir.mkdir(parents=True)
        (event_dir / "test-direction.md").write_text(
            "# Conation\n\nObserved/recorded: 2026-09-04\n"
            "Event: ADD\nSubject: Private direction\n"
            "Current status: PRESENT / EXPLORATORY\n\n"
            "## Provenance\n\n2026-09-04 conversation\n",
            encoding="utf-8",
        )
        (self.root / "EVENT_INDEX.md").write_text(
            "[one](./events/2026-09-04/test-direction.md)\n",
            encoding="utf-8",
        )
        self.manifest = build_manifest(self.root)

    def test_real_manifest_roundtrip_is_historical_only_and_frozen(self):
        evidence = historical_context(self.manifest)
        self.assertEqual(evidence, parse_history_export(json.dumps(self.manifest)))
        self.assertEqual(1, len(evidence))
        self.assertEqual("HISTORICAL_ONLY", evidence[0].evidence_class)
        self.assertEqual("ADD", evidence[0].event_type)
        self.assertEqual(
            {"event_date", "event_type", "content_sha256", "evidence_class"},
            {field.name for field in fields(HistoricalConationEvidence)},
        )
        with self.assertRaises(FrozenInstanceError):
            evidence[0].evidence_class = "CURRENT"
        with self.assertRaises(TypeError):
            HistoricalConationEvidence("2026-09-04", "ADD", "a" * 64, "CURRENT")

    def test_private_status_present_is_explicitly_discarded(self):
        privileged_export = build_manifest(
            self.root, include_path=True, include_subject=True, include_status=True
        )
        self.assertIn("PRESENT", privileged_export["events"][0]["recorded_status"])
        history = historical_context(privileged_export)
        output = repr(history)
        for sensitive in ("PRESENT", "Private direction", "test-direction.md"):
            self.assertNotIn(sensitive, output)
        self.assertNotIn("status", {field.name for field in fields(history[0])})

    def test_forged_currentness_and_authority_fail_closed(self):
        for key, forged in (
            ("currentness", "current"),
            ("effect_authority", "write"),
            ("activation", "active"),
            ("schema", "conations.signal.v1"),
        ):
            with self.subTest(key=key):
                suspect = {**self.manifest, key: forged}
                with self.assertRaises(HistoryContextError):
                    historical_context(suspect)

    def test_forged_signal_desire_and_consent_fields_fail_closed(self):
        for key, value in (
            ("status_currentness", "current"),
            ("drive_kind", "CURIOSITY"),
            ("current_want", True),
            ("magnitude", 1.0),
            ("confidence", 1.0),
            ("consent", True),
            ("activation", "ready"),
        ):
            with self.subTest(key=key):
                forged = dict(self.manifest["events"][0])
                forged[key] = value
                with self.assertRaises(HistoryContextError):
                    historical_context({**self.manifest, "events": [forged]})

    def test_lowercase_revocation_cannot_sneak_in(self):
        forged = {**self.manifest["events"][0], "event_type": "revoke"}
        with self.assertRaises(HistoryContextError):
            historical_context({**self.manifest, "events": [forged]})

    def test_revoked_and_completed_events_never_become_present(self):
        for terminal_kind in ("REVOKE", "COMPLETE"):
            event = {**self.manifest["events"][0], "event_type": terminal_kind}
            evidence = historical_context({**self.manifest, "events": [event]})[0]
            self.assertEqual("HISTORICAL_ONLY", evidence.evidence_class)
            self.assertFalse(hasattr(evidence, "activation"))
            self.assertFalse(hasattr(evidence, "signal"))

    def test_duplicate_json_keys_rejected(self):
        encoded = json.dumps(self.manifest)
        duplicated = encoded.replace(
            '"currentness": "history_only"',
            '"currentness": "current", "currentness": "history_only"',
        )
        with self.assertRaises(HistoryContextError):
            parse_history_export(duplicated)
        with self.assertRaises(HistoryContextError):
            parse_history_export("{" + '"events": []' + ", " + '"events": []' + "}")

    def test_invalid_private_field_and_oversized_input_rejected(self):
        event = {**self.manifest["events"][0], "recorded_status": {"active": True}}
        with self.assertRaises(HistoryContextError):
            historical_context({**self.manifest, "events": [event]})
        with self.assertRaises(HistoryContextError):
            parse_history_export(" " * 1_048_577)

    def test_bad_digest_dates_types_or_oversized_batches_rejected(self):
        event = self.manifest["events"][0]
        for modified in (
            {**event, "event_date": "2026-02-30"},
            {**event, "event_date": "2026-9-4"},
            {**event, "content_sha256": "bad"},
            {**event, "content_sha256": event["content_sha256"].upper()},
            {**event, "event_type": None},
            {**event, "status_currentness": True},
        ):
            with self.subTest(modified=modified):
                with self.assertRaises(HistoryContextError):
                    historical_context({**self.manifest, "events": [modified]})
        with self.assertRaises(HistoryContextError):
            historical_context({**self.manifest, "events": [event] * (MAX_HISTORICAL_EVENTS + 1)})


if __name__ == "__main__":
    unittest.main()
