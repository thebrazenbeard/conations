"""Strict read-only context for consumers of Conations history exports.

This module deliberately has no Volition Signal, activation, drive, or task
constructor. A historical conation is evidence for fresh appraisal, never a
claim that a particular desire remains current or is self-authored.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from conation_manifest import EVENT_KINDS


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_OPTIONAL_PRIVATE_FIELDS = frozenset({"path", "subject", "recorded_status"})
_EVENT_FIELDS = frozenset({"event_date", "event_type", "content_sha256", "status_currentness"})
MAX_HISTORICAL_EVENTS = 1000


class HistoryContextError(ValueError):
    """An export is not valid historical context for a consumer."""


@dataclass(frozen=True, slots=True)
class HistoricalConationEvidence:
    """Non-authoritative source metadata without currentness or motive strength."""

    event_date: str
    event_type: str
    content_sha256: str
    evidence_class: str = field(init=False, default="HISTORICAL_ONLY")


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HistoryContextError("duplicate JSON field in history export")
        result[key] = value
    return result


def historical_context(manifest: Mapping[str, Any]) -> tuple[HistoricalConationEvidence, ...]:
    """Validate a Conations export and keep only historical evidence locators.

    Private optional exports are allowed as input but their subject, path and
    recorded status are never returned. Any unrecognized field fails closed,
    including forged ``drive_kind``, ``current_want``, ``magnitude``, or
    ``consent``. Caller must independently obtain *fresh* evidence for Volition.
    """
    if not isinstance(manifest, Mapping) or set(manifest) != {
        "schema", "currentness", "effect_authority", "activation", "events"
    }:
        raise HistoryContextError("invalid Conations export envelope")
    if (manifest["schema"], manifest["currentness"], manifest["effect_authority"], manifest["activation"]) != (
        "conations.history.v1", "history_only", "none", "fresh_reappraisal_required"
    ):
        raise HistoryContextError("Conations history cannot assert a current want or authority")
    events = manifest["events"]
    if type(events) is not list or len(events) > MAX_HISTORICAL_EVENTS:
        raise HistoryContextError("invalid or oversized historical evidence batch")
    output: list[HistoricalConationEvidence] = []
    for item in events:
        if not isinstance(item, Mapping):
            raise HistoryContextError("invalid historical evidence entry")
        fields = set(item)
        if not _EVENT_FIELDS <= fields or not fields <= (_EVENT_FIELDS | _OPTIONAL_PRIVATE_FIELDS):
            raise HistoryContextError("unrecognized or missing historical evidence fields")
        if any(type(item[key]) is not str for key in fields & _OPTIONAL_PRIVATE_FIELDS):
            raise HistoryContextError("invalid historical private metadata")
        if item["status_currentness"] != "historical_only":
            raise HistoryContextError("historical event cannot assert currentness")
        day, kind, digest = item["event_date"], item["event_type"], item["content_sha256"]
        if type(day) is not str or not _DATE.fullmatch(day):
            raise HistoryContextError("invalid historical date")
        try:
            date.fromisoformat(day)
        except ValueError as exc:
            raise HistoryContextError("invalid historical date") from exc
        if type(kind) is not str or kind not in EVENT_KINDS:
            raise HistoryContextError("invalid historical lifecycle kind")
        if type(digest) is not str or not _SHA256.fullmatch(digest):
            raise HistoryContextError("invalid historical content digest")
        output.append(HistoricalConationEvidence(day, kind, digest))
    return tuple(output)


def parse_history_export(raw: str | bytes) -> tuple[HistoricalConationEvidence, ...]:
    """Safely parse a JSON export without losing duplicate-key attacks."""
    if not isinstance(raw, (str, bytes)):
        raise HistoryContextError("history export must be JSON text")
    if len(raw) > 1_048_576:
        raise HistoryContextError("historical export exceeds size limit")
    try:
        manifest = json.loads(raw, object_pairs_hook=_reject_duplicate_json_keys)
    except (ValueError, UnicodeError) as exc:
        raise HistoryContextError("malformed historical export JSON") from exc
    return historical_context(manifest)
