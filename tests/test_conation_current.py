"""Fresh present conation candidates are not historical records or permissions."""

import unittest
import re
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier, BrokenBarrierError, Event, Thread
from unittest.mock import patch

from conation_current import (
    ConationOrigin,
    ConationCurrentError,
    CurrentConationEngine,
    CurrentConationObservation,
)
from conation_history_context import HistoricalConationEvidence


NOW = datetime(2026, 11, 6, 21, 0, tzinfo=timezone.utc)


def observed(
    conation_id="curiosity",
    observation_id="observation-1",
    statement="Explore a new hypothesis",
    priority=0.7,
    **changes,
):
    values = dict(
        conation_id=conation_id,
        observation_id=observation_id,
        subject_id="vera",
        runtime_instance_id="instance-a",
        model_revision="model-20261106",
        origin=ConationOrigin.MODEL_PROPOSAL,
        statement=statement,
        source_ref="runtime-observation-1",
        priority=priority,
        observed_at=NOW,
        expires_at=NOW + timedelta(seconds=180),
    )
    return CurrentConationObservation(**(values | changes))


def engine():
    return CurrentConationEngine(
        subject_id="vera",
        runtime_instance_id="instance-a",
        model_revision="model-20261106",
    )


class CurrentConationTests(unittest.TestCase):
    def test_concurrent_observations_cannot_both_pass_same_generation(self):
        live = engine()
        rendezvous = Barrier(2)
        original_validate = CurrentConationEngine._validate_observation
        results = []

        def coordinated_validate(candidate, now):
            validated = original_validate(candidate, now)
            try:
                rendezvous.wait(timeout=0.5)
            except BrokenBarrierError:
                # Expected with a serialized engine: the second thread cannot
                # reach validation until the first one has committed.
                pass
            return validated

        def submit(candidate):
            try:
                result = live.observe(candidate, now=NOW, expected_generation=0)
                results.append(("accepted", result.generation))
            except ConationCurrentError as error:
                results.append(("rejected", str(error)))

        with patch.object(CurrentConationEngine, "_validate_observation",
                          staticmethod(coordinated_validate)):
            workers = [
                Thread(target=submit, args=(observed("first", "concurrent-first"),)),
                Thread(target=submit, args=(observed("second", "concurrent-second"),)),
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=3)
            self.assertFalse(any(worker.is_alive() for worker in workers))

        self.assertEqual(sum(kind == "accepted" for kind, _ in results), 1)
        self.assertEqual(sum(kind == "rejected" for kind, _ in results), 1)
        self.assertEqual(live.snapshot(now=NOW).generation, 1)
        self.assertEqual(len(live.snapshot(now=NOW).candidates), 1)

    def test_close_serializes_with_inflight_observation(self):
        live = engine()
        validating = Event()
        release_validation = Event()
        close_started = Event()
        close_done = Event()
        outcomes = []
        original_validate = CurrentConationEngine._validate_observation

        def paused_validate(candidate, now):
            validated = original_validate(candidate, now)
            validating.set()
            if not release_validation.wait(timeout=3):
                raise AssertionError("test synchronization timed out")
            return validated

        def submit():
            try:
                outcomes.append(("observe", live.observe(
                    observed(), now=NOW, expected_generation=0,
                ).generation))
            except Exception as error:
                outcomes.append(("observe_error", type(error).__name__))

        def shutdown():
            close_started.set()
            live.close()
            close_done.set()

        with patch.object(CurrentConationEngine, "_validate_observation",
                          staticmethod(paused_validate)):
            observer = Thread(target=submit)
            closer = Thread(target=shutdown)
            observer.start()
            try:
                self.assertTrue(validating.wait(timeout=3))
                closer.start()
                self.assertTrue(close_started.wait(timeout=3))
                self.assertFalse(close_done.wait(timeout=0.15))
            finally:
                release_validation.set()
            observer.join(timeout=3)
            closer.join(timeout=3)
            self.assertFalse(observer.is_alive())
            self.assertFalse(closer.is_alive())

        self.assertEqual(outcomes, [("observe", 1)])
        self.assertTrue(close_done.is_set())
        with self.assertRaises(ConationCurrentError):
            live.snapshot(now=NOW)

    def test_documented_minimal_example_executes(self):
        docs = (Path(__file__).resolve().parents[1] / "docs" /
                "CURRENT_CONATION_CONTRACT_V1.md").read_text(encoding="utf-8")
        snippet = re.search(r"## Minimal local example\s+```python\n(.*?)\n```",
                            docs, flags=re.DOTALL)
        self.assertIsNotNone(snippet, "the public contract must contain a Python example")
        exec(compile(snippet.group(1), "CURRENT_CONATION_CONTRACT_V1.md", "exec"), {})

    def test_fresh_observation_is_live_non_authorizing_runtime_candidate(self):
        live = engine()
        state = live.observe(observed(), now=NOW, expected_generation=0)
        self.assertEqual(state.schema, "conations.current.v1")
        self.assertEqual(state.currentness, "runtime_ephemeral")
        self.assertEqual(state.state_status, "CANDIDATES_REPORTED")
        self.assertEqual(state.effect_authority, "none")
        self.assertEqual(state.generation, 1)
        self.assertEqual(len(state.candidates), 1)
        self.assertEqual(state.candidates[0].statement, "Explore a new hypothesis")
        self.assertEqual(state.candidates[0].priority, 0.7)
        self.assertIs(state.candidates[0].origin, ConationOrigin.MODEL_PROPOSAL)
        for prohibited in ("consent", "authorized", "task", "execute", "action_permission"):
            self.assertFalse(hasattr(state, prohibited))
        with self.assertRaises(FrozenInstanceError):
            state.effect_authority = "yes"

    def test_ranking_and_expiry_are_current_view_not_persistent_history(self):
        live = engine()
        live.observe(observed(), now=NOW, expected_generation=0)
        live.observe(
            observed("rest", "observation-2", "Pause", 0.9),
            now=NOW, expected_generation=1,
        )
        ranked = live.snapshot(now=NOW)
        self.assertEqual([item.conation_id for item in ranked.candidates], ["rest", "curiosity"])
        expired = live.snapshot(now=NOW + timedelta(seconds=181))
        self.assertEqual(expired.candidates, ())
        self.assertEqual(expired.generation, 2)
        with self.assertRaises(ConationCurrentError):
            live.withdraw("rest", now=NOW + timedelta(seconds=181), expected_generation=2)
        with self.assertRaises(ConationCurrentError):
            live.snapshot(now=NOW + timedelta(seconds=1))
        with self.assertRaises(ConationCurrentError):
            live.observe(observed("rest", "observation-3"), now=NOW + timedelta(seconds=181), expected_generation=2)

    def test_freshness_requires_exact_subject_runtime_and_model_binding(self):
        bound = engine()
        with self.assertRaises(AttributeError):
            bound.subject_id = "brigit"
        for changes in (
            {"subject_id": "brigit"},
            {"runtime_instance_id": "old-instance"},
            {"model_revision": "other-model"},
            {"observed_at": NOW + timedelta(seconds=1)},
            {"observed_at": NOW - timedelta(seconds=31)},
            {"expires_at": NOW + timedelta(seconds=301)},
            {"expires_at": NOW},
        ):
            with self.subTest(changes=changes):
                live = engine()
                with self.assertRaises(ConationCurrentError):
                    live.observe(observed(**changes), now=NOW, expected_generation=0)
                self.assertEqual(live.snapshot(now=NOW).generation, 0)

    def test_replay_conflict_and_cas_prevent_silent_reinterpretation(self):
        live = engine()
        first = observed()
        live.observe(first, now=NOW, expected_generation=0)
        same = live.observe(first, now=NOW, expected_generation=1)
        self.assertEqual(same.generation, 1)
        with self.assertRaises(ConationCurrentError):
            live.observe(observed(statement="Changed"), now=NOW, expected_generation=1)
        with self.assertRaises(ConationCurrentError):
            live.observe(observed("other", "observation-2"), now=NOW, expected_generation=0)
        with self.assertRaises(ConationCurrentError):
            live.observe(
                observed(observation_id="observation-2", observed_at=NOW),
                now=NOW, expected_generation=1,
            )

    def test_withdrawal_removes_current_candidate_and_blocks_old_replay(self):
        live = engine()
        first = observed()
        live.observe(first, now=NOW, expected_generation=0)
        remaining = live.withdraw("curiosity", now=NOW, expected_generation=1)
        self.assertEqual(remaining.candidates, ())
        self.assertEqual(remaining.generation, 2)
        with self.assertRaises(ConationCurrentError):
            live.observe(first, now=NOW, expected_generation=2)
        with self.assertRaises(ConationCurrentError):
            live.withdraw("curiosity", now=NOW, expected_generation=2)

    def test_invalid_observations_rejected_without_leaking_statement(self):
        for changes in (
            {"priority": True},
            {"priority": float("nan")},
            {"priority": float("inf")},
            {"priority": -0.1},
            {"priority": 1.1},
            {"statement": ""},
            {"statement": "Private\x1b[31m"},
            {"statement": "x" * 1001},
            {"source_ref": "C:/private/file"},
            {"origin": "MODEL_PROPOSAL"},
            {"origin": "HOST_ATTESTED"},
            {"origin": None},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(ConationCurrentError):
                    engine().observe(observed(**changes), now=NOW, expected_generation=0)
        private = observed(statement="Sensitive current thought", source_ref="source-private")
        self.assertNotIn("Sensitive", repr(private))
        self.assertNotIn("source-private", repr(private))

    def test_distinct_typed_origin_classes_do_not_promote_authority(self):
        for origin in ConationOrigin:
            with self.subTest(origin=origin):
                state = engine().observe(
                    observed(origin=origin), now=NOW, expected_generation=0,
                )
                self.assertIs(state.candidates[0].origin, origin)
                self.assertEqual(state.evidence_class, "UNVERIFIED_CURRENT_OBSERVATIONS")
                self.assertEqual(state.effect_authority, "none")

    def test_expired_candidates_release_capacity_without_replay_resurrection(self):
        live = engine()
        for index in range(32):
            live.observe(
                observed(
                    f"want{index:02d}", f"observation-{index:02d}",
                    expires_at=NOW + timedelta(seconds=60),
                ),
                now=NOW, expected_generation=index,
            )
        self.assertEqual(len(live.snapshot(now=NOW).candidates), 32)
        with self.assertRaises(ConationCurrentError):
            live.observe(observed("overflow", "observation-32"), now=NOW, expected_generation=32)
        now = NOW + timedelta(seconds=61)
        self.assertEqual(live.snapshot(now=now).state_status, "UNKNOWN")
        state = live.observe(
            observed("new-current", "observation-32", observed_at=now,
                     expires_at=now + timedelta(seconds=60)),
            now=now, expected_generation=32,
        )
        self.assertEqual(state.generation, 33)
        self.assertEqual([x.conation_id for x in state.candidates], ["new-current"])
        with self.assertRaises(ConationCurrentError):
            live.observe(
                observed("want00", "observation-00", observed_at=now,
                         expires_at=now + timedelta(seconds=60)),
                now=now, expected_generation=33,
            )

    def test_historical_export_cannot_be_admitted_as_present_observation(self):
        historical = HistoricalConationEvidence("2026-09-04", "ADD", "a" * 64)
        with self.assertRaises(ConationCurrentError):
            engine().observe(historical, now=NOW, expected_generation=0)
        self.assertNotIn("historical", {field.name for field in fields(CurrentConationObservation)})

    def test_close_discards_runtime_state_and_denies_further_use(self):
        live = engine()
        live.observe(observed(), now=NOW, expected_generation=0)
        live.close()
        with self.assertRaises(ConationCurrentError):
            live.snapshot(now=NOW)
        with self.assertRaises(ConationCurrentError):
            live.observe(observed("again", "observation-2"), now=NOW, expected_generation=2)

    def test_cold_restart_returns_unknown_not_inferred_absence_or_hydration(self):
        before = engine()
        self.assertEqual(before.snapshot(now=NOW).state_status, "UNKNOWN")
        before.observe(observed(), now=NOW, expected_generation=0)
        self.assertEqual(before.snapshot(now=NOW).state_status, "CANDIDATES_REPORTED")
        restarted = engine()  # Same label, separate local instance.
        cold = restarted.snapshot(now=NOW + timedelta(seconds=1))
        self.assertEqual(cold.state_status, "UNKNOWN")
        self.assertEqual(cold.candidates, ())
        self.assertEqual(cold.generation, 0)
        self.assertEqual(cold.effect_authority, "none")


if __name__ == "__main__":
    unittest.main()
