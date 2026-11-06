"""Ephemeral present conation candidates, independent from historical exports.

This engine holds fresh observations for local reasoning. It neither infers
desire from dated records nor grants a task, consent, or action authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
import math
import re
from threading import RLock


FRESHNESS_SECONDS = 30
MAX_TTL_SECONDS = 300
MAX_CANDIDATES = 32
MAX_OBSERVATIONS_PER_INSTANCE = 256
_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,95}\Z")


class ConationCurrentError(ValueError):
    """A candidate is not eligible for this exact ephemeral runtime instance."""


class ConationOrigin(str, Enum):
    """Caller-claimed origin classification; never an identity attestation."""

    MODEL_PROPOSAL = "MODEL_PROPOSAL"
    RUNTIME_SELF_REPORT = "RUNTIME_SELF_REPORT"
    HOST_OBSERVATION = "HOST_OBSERVATION"


def _serialized(method):
    """Serialize a single engine's lifecycle, including nested snapshots."""

    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return call


def _opaque(value: object) -> bool:
    return type(value) is str and _OPAQUE.fullmatch(value) is not None


def _utc(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ConationCurrentError("a timezone-aware observation time is required")
    return value.astimezone(timezone.utc)


def _statement(value: object) -> bool:
    return (
        type(value) is str
        and 0 < len(value) <= 1000
        and bool(value.strip())
        and not any(
            (ord(c) < 32 and c not in "\n\t")
            or 0x7F <= ord(c) <= 0x9F
            or 0xD800 <= ord(c) <= 0xDFFF
            for c in value
        )
    )


@dataclass(frozen=True, slots=True)
class CurrentConationObservation:
    """Reported fresh conative orientation, not proof of private experience.

    Callers are responsible for binding the claimed runtime and source; this
    plain Python object is not an authenticated attestation by itself.
    """

    conation_id: str
    observation_id: str
    subject_id: str
    runtime_instance_id: str
    model_revision: str
    origin: ConationOrigin
    statement: str = field(repr=False)
    source_ref: str = field(repr=False)
    priority: float
    observed_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class CurrentConationSnapshot:
    """Currently eligible candidates for reasoning, never action orders."""

    subject_id: str
    runtime_instance_id: str
    model_revision: str
    generation: int
    candidates: tuple[CurrentConationObservation, ...]
    state_status: str
    schema: str = field(init=False, default="conations.current.v1")
    currentness: str = field(init=False, default="runtime_ephemeral")
    evidence_class: str = field(init=False, default="UNVERIFIED_CURRENT_OBSERVATIONS")
    effect_authority: str = field(init=False, default="none")


class CurrentConationEngine:
    """In-memory, bound, compare-and-swap current-candidate evaluator.

    New runtime instances start empty. An expired item disappears from all
    current snapshots; nothing here persists or imports historical exports.
    """

    __slots__ = (
        "_subject_id", "_runtime_instance_id", "_model_revision",
        "_active", "_seen", "_generation", "_closed", "_last_evaluation", "_lock",
    )

    def __init__(self, *, subject_id: str, runtime_instance_id: str, model_revision: str):
        if not all(_opaque(value) for value in (subject_id, runtime_instance_id, model_revision)):
            raise ConationCurrentError("invalid runtime binding")
        self._subject_id = subject_id
        self._runtime_instance_id = runtime_instance_id
        self._model_revision = model_revision
        self._active: dict[str, CurrentConationObservation] = {}
        self._seen: dict[str, CurrentConationObservation] = {}
        self._generation = 0
        self._closed = False
        self._last_evaluation: datetime | None = None
        self._lock = RLock()

    @property
    def subject_id(self) -> str:
        return self._subject_id

    @property
    def runtime_instance_id(self) -> str:
        return self._runtime_instance_id

    @property
    def model_revision(self) -> str:
        return self._model_revision

    def _require_open(self) -> None:
        if self._closed:
            raise ConationCurrentError("runtime instance is closed")

    def _require_generation(self, expected_generation: int) -> None:
        if type(expected_generation) is not int or expected_generation != self._generation:
            raise ConationCurrentError("stale current-conation generation")

    def _checked_time(self, now: datetime) -> datetime:
        instant = _utc(now)
        if self._last_evaluation is not None and instant < self._last_evaluation:
            raise ConationCurrentError("runtime clock moved backward")
        return instant

    @staticmethod
    def _validate_observation(observation: object, now: datetime) -> CurrentConationObservation:
        if type(observation) is not CurrentConationObservation:
            raise ConationCurrentError("fresh typed observation required")
        values = (
            observation.conation_id, observation.observation_id, observation.subject_id,
            observation.runtime_instance_id, observation.model_revision, observation.source_ref,
        )
        if not all(_opaque(value) for value in values) or not _statement(observation.statement):
            raise ConationCurrentError("invalid current conation data")
        if type(observation.origin) is not ConationOrigin:
            raise ConationCurrentError("typed current conation origin required")
        strength = observation.priority
        if type(strength) not in (float, int) or not math.isfinite(strength) or not 0 <= strength <= 1:
            raise ConationCurrentError("invalid current priority")
        sampled = _utc(observation.observed_at)
        expires = _utc(observation.expires_at)
        if (
            sampled > now
            or now - sampled > timedelta(seconds=FRESHNESS_SECONDS)
            or expires <= now
            or expires <= sampled
            or expires - sampled > timedelta(seconds=MAX_TTL_SECONDS)
        ):
            raise ConationCurrentError("current observation not fresh and bounded")
        return observation

    @_serialized
    def snapshot(self, *, now: datetime) -> CurrentConationSnapshot:
        self._require_open()
        instant = self._checked_time(now)
        active = tuple(
            sorted(
                (candidate for candidate in self._active.values()
                 if _utc(candidate.expires_at) > instant),
                key=lambda item: (-item.priority, item.conation_id),
            )
        )
        self._last_evaluation = instant
        return CurrentConationSnapshot(
            self.subject_id, self.runtime_instance_id, self.model_revision,
            self._generation, active,
            "CANDIDATES_REPORTED" if active else "UNKNOWN",
        )

    @_serialized
    def observe(
        self, observation: CurrentConationObservation, *,
        now: datetime, expected_generation: int,
    ) -> CurrentConationSnapshot:
        self._require_open()
        self._require_generation(expected_generation)
        instant = self._checked_time(now)
        candidate = self._validate_observation(observation, instant)
        if (
            candidate.subject_id != self.subject_id
            or candidate.runtime_instance_id != self.runtime_instance_id
            or candidate.model_revision != self.model_revision
        ):
            raise ConationCurrentError("cross-runtime or cross-subject observation")
        # Expiry frees *active* capacity, never the replay ledger. Build the
        # eligible view first; do not mutate the live store on a failed call.
        current = {
            key: value for key, value in self._active.items()
            if _utc(value.expires_at) > instant
        }
        prior = self._seen.get(candidate.observation_id)
        if prior is not None:
            if prior != candidate or current.get(candidate.conation_id) != candidate:
                raise ConationCurrentError("observation replay conflict or withdrawn record")
            return self.snapshot(now=instant)
        active = current.get(candidate.conation_id)
        if active is not None and _utc(candidate.observed_at) <= _utc(active.observed_at):
            raise ConationCurrentError("reappraisal did not advance observation time")
        if len(self._seen) >= MAX_OBSERVATIONS_PER_INSTANCE:
            raise ConationCurrentError("runtime observation budget exhausted")
        if active is None and len(current) >= MAX_CANDIDATES:
            raise ConationCurrentError("current candidate capacity exhausted")
        self._active = current
        self._seen[candidate.observation_id] = candidate
        self._active[candidate.conation_id] = candidate
        self._generation += 1
        return self.snapshot(now=instant)

    @_serialized
    def withdraw(
        self, conation_id: str, *, now: datetime, expected_generation: int
    ) -> CurrentConationSnapshot:
        self._require_open()
        self._require_generation(expected_generation)
        instant = self._checked_time(now)
        if (
            not _opaque(conation_id)
            or conation_id not in self._active
            or _utc(self._active[conation_id].expires_at) <= instant
        ):
            raise ConationCurrentError("no current conation to withdraw")
        del self._active[conation_id]
        self._generation += 1
        return self.snapshot(now=instant)

    @_serialized
    def close(self) -> None:
        self._active.clear()
        self._seen.clear()
        self._closed = True
        self._generation += 1
