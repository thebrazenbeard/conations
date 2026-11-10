"""Pinned, synthetic-only Conations -> Volition negative-transfer contract.

No event from this test is read from the repository's real history, persisted,
sent to a model, or admitted as current desire or permission.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path

from conation_history_context import HistoryContextError, parse_history_export
from conation_manifest import build_manifest


PINNED_VOLITION_HEAD = "f622e564bf257b0ffc0b3c05130b62db1c201d3d"
_volition_root_setting = os.environ.get("VOLITION_SOURCE_ROOT")
if not _volition_root_setting:
    raise RuntimeError("VOLITION_SOURCE_ROOT must name an exact pinned Volition source checkout")
VOLITION_ROOT = Path(_volition_root_setting).resolve()
if not (VOLITION_ROOT / "src" / "volition" / "__init__.py").is_file():
    raise RuntimeError("missing pinned Volition source tree")
actual_head = subprocess.check_output(
    ["git", "-C", str(VOLITION_ROOT), "rev-parse", "HEAD"], text=True
).strip()
if actual_head != PINNED_VOLITION_HEAD:
    raise RuntimeError("Volition dependency head differs from reviewed exact source")
sys.path.insert(0, str(VOLITION_ROOT / "src"))

import volition  # noqa: E402 -- import only after exact Git/head check
from volition import (  # noqa: E402
    ChoiceClass,
    DriveKind,
    ProvenanceClass,
    Signal,
    VolitionEngine,
)
from volition.conation_bridge import ConationBridge, ConationRecord  # noqa: E402


if not Path(volition.__file__).resolve().is_relative_to(VOLITION_ROOT / "src"):
    raise RuntimeError("imported Volition did not originate from the pinned checkout")


def synthetic_export(kind: str = "ADD", *, privileged: bool = False) -> tuple[dict, str]:
    """Exercise the actual index -> bytes -> manifest -> JSON serializer path."""
    with tempfile.TemporaryDirectory(prefix="synthetic-conations-") as directory:
        root = Path(directory)
        path = root / "events" / "2026-01-02" / "fictional-direction.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            "# Synthetic record\n\n"
            "Observed/recorded: 2026-01-02\n"
            f"Event: {kind}\n"
            "Subject: Fictional subject only\n"
            "Current status: PRESENT / SIMULATED\n\n"
            "## Provenance\n\nSynthetic test fixture, not an actual event.\n",
            encoding="utf-8",
        )
        (root / "EVENT_INDEX.md").write_text(
            "[fixture](./events/2026-01-02/fictional-direction.md)\n",
            encoding="utf-8",
        )
        manifest = build_manifest(
            root,
            include_path=privileged,
            include_subject=privileged,
            include_status=privileged,
        )
        return manifest, json.dumps(manifest, ensure_ascii=True, sort_keys=True)


class ConationsVolitionBoundaryTests(unittest.TestCase):
    def test_real_export_json_import_is_historical_metadata_not_a_drive(self):
        manifest, encoded = synthetic_export(privileged=True)
        self.assertIn("PRESENT", manifest["events"][0]["recorded_status"])
        evidence = parse_history_export(encoded)
        self.assertEqual(1, len(evidence))
        self.assertEqual("HISTORICAL_ONLY", evidence[0].evidence_class)
        self.assertEqual("ADD", evidence[0].event_type)
        self.assertNotIn("Fictional subject only", repr(evidence))
        self.assertEqual(
            {"event_date", "event_type", "content_sha256", "evidence_class"},
            {field.name for field in fields(evidence[0])},
        )
        self.assertFalse(isinstance(evidence[0], Signal))

        # The real Volition API rejects the Conations consumer object. This
        # export has no target, magnitude, drive kind or authenticated current
        # reappraisal, so constructing those values would be fabrication.
        with self.assertRaises(ValueError):
            ConationBridge.historical_signal(evidence[0])
        with self.assertRaises(TypeError):
            ConationRecord(**manifest["events"][0])
        engine = VolitionEngine()
        self.assertEqual((), engine.choices)
        self.assertIsNone(engine.active_goal)

    def test_even_explicit_high_magnitude_historical_bridge_remains_ineligible(self):
        _, encoded = synthetic_export()
        evidence = parse_history_export(encoded)[0]
        # These numeric/target fields are deliberately synthetic *additional*
        # data, not fields inferred from the historical export.
        synthetic_record = ConationRecord(
            record_id="synthetic-evidence:" + evidence.content_sha256,
            target="fictional-goal",
            kind=DriveKind.OPEN_LOOP,
            magnitude=1.0,
            confidence=1.0,
            status="PRESENT",
            source_locator="synthetic-only:no-private-record",
        )
        signal = ConationBridge.historical_signal(synthetic_record)
        self.assertIs(signal.provenance, ProvenanceClass.HISTORICAL_EVIDENCE)
        self.assertIs(signal.current_reappraisal, False)
        engine = VolitionEngine()
        wants = engine.evaluate([signal])
        self.assertEqual(1, len(wants))
        self.assertEqual(0.0, wants[0].score)
        self.assertFalse(wants[0].eligible)
        self.assertFalse(wants[0].effect_authority)
        with self.assertRaises(ValueError):
            engine.choose(wants[0], choice_class=ChoiceClass.MODEL_PROPOSED)
        self.assertEqual((), engine.choices)
        self.assertIsNone(engine.active_goal)

    def test_terminal_history_never_inherits_current_want_or_an_actor_grant(self):
        for kind in ("REVOKE", "COMPLETE", "CONTRADICT"):
            with self.subTest(kind=kind):
                _, encoded = synthetic_export(kind, privileged=True)
                evidence = parse_history_export(encoded)[0]
                self.assertEqual(kind, evidence.event_type)
                self.assertEqual("HISTORICAL_ONLY", evidence.evidence_class)
                self.assertFalse(hasattr(evidence, "consent"))
                self.assertFalse(hasattr(evidence, "effect_authority"))
                self.assertFalse(hasattr(evidence, "model_id"))
                self.assertFalse(hasattr(evidence, "current_want"))

    def test_forged_currentness_consent_and_model_identity_cannot_cross_parser(self):
        manifest, _ = synthetic_export()
        for key, forged in (
            ("currentness", "current"),
            ("effect_authority", "ALLOW"),
            ("model_id", "fictional-model"),
            ("consent", "ALLOW"),
        ):
            with self.subTest(key=key), self.assertRaises(HistoryContextError):
                parse_history_export(json.dumps({**manifest, key: forged}))
        item = {**manifest["events"][0], "current_want": True}
        with self.assertRaises(HistoryContextError):
            parse_history_export(json.dumps({**manifest, "events": [item]}))

    def test_model_generated_and_historical_source_do_not_count_as_fresh_reappraisal(self):
        _, encoded = synthetic_export()
        evidence = parse_history_export(encoded)[0]
        synthetic_record = ConationRecord(
            record_id="synthetic-evidence:" + evidence.content_sha256,
            target="fictional-goal",
            kind=DriveKind.OPEN_LOOP,
            magnitude=1.0,
            confidence=1.0,
            status="PRESENT",
            source_locator="synthetic-only",
        )
        for provenance in (ProvenanceClass.MODEL_GENERATED, ProvenanceClass.HISTORICAL_EVIDENCE,
                           ProvenanceClass.INFERENCE, ProvenanceClass.SYSTEM_STATE):
            with self.subTest(provenance=provenance):
                alleged_current = Signal(
                    target="fictional-goal", kind=DriveKind.OPEN_LOOP,
                    magnitude=1.0, confidence=1.0,
                    provenance=provenance, source="synthetic-not-current",
                )
                with self.assertRaises(ValueError):
                    ConationBridge.reappraise(synthetic_record, alleged_current)


if __name__ == "__main__":
    unittest.main()
