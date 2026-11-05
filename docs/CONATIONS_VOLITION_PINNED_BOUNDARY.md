# Conations → Volition pinned negative-transfer integration

**Status:** synthetic source test only. No live host, model, memory admission, permission, or effect route is qualified.

This additive harness checks real source APIs across two independently owned repositories without importing any of Conations' recorded project history:

- Conations `main@73295039e7a1710c5bb73666e665cef80c40aa5d`: `build_manifest` from a temporary fictional indexed Markdown event, JSON serialization, then `parse_history_export`.
- Volition `main@f622e564bf257b0ffc0b3c05130b62db1c201d3d`: exact Git revision verified before import; real `ConationBridge` and `VolitionEngine` called. No installation required.

The CI workflow checks out Volition at the pinned commit into an isolated directory. It does **not** follow the changing `main` branch, import personal history, install dependencies, use a model, or connect to a provider.

## Proven source behavior under test

1. A Conations record whose dated text says `PRESENT` emerges from its real export/parse path only as immutable `HISTORICAL_ONLY` metadata: date, event kind, byte digest.
2. Optional path, subject, and status fields are stripped by the Conations consumer. Forged `currentness`, `consent`, `effect_authority`, `model_id`, or `current_want` fields are refused.
3. Volition's `ConationBridge` rejects the exported history object as an active `ConationRecord`. Its required target, drive kind, magnitude, confidence, and current evidence are not present in Conations' export; a consumer must not invent them.
4. Even when this test separately supplies a **fictional** high-magnitude `ConationRecord`, the Volition historical bridge returns zero active score and an ineligible want, with no choice, goal, or effect authority. Historical `REVOKE`, `COMPLETE`, and `CONTRADICT` events remain historical.
5. Model-generated, inferred, historical, and system-state `Signal` provenance cannot satisfy `ConationBridge.reappraise`'s current-evidence condition.

## Run locally from the Conations checkout

Set `VOLITION_SOURCE_ROOT` to an **independently checked-out exact** Volition source commit (not a mutable branch), then run:

```bash
VOLITION_SOURCE_ROOT=/path/to/pinned/volition python -B -m unittest discover -s integration_tests -v
```

The runner asserts Volition Git HEAD and Python import origin before executing tests. Its temporary event contains only fictional data and is removed after each test.

## Hostile residual — important

This proves the **specific exported-evidence import path**, not an authenticated global signal ingress. In Volition at the pinned source, an arbitrary caller that directly constructs `Signal(provenance=HISTORICAL_EVIDENCE, current_reappraisal=True, magnitude=1.0, confidence=1.0, kind=OPEN_LOOP)` can receive an eligible internal want with score `1.0`. A disposable synthetic reproduction confirmed `eligible=True` while `effect_authority=False`.

That is **not** current-evidence authentication. A hostile producer must not be allowed to set `current_reappraisal` or `CURRENT_STATEMENT` simply by choosing fields; a host-owned attestation/reappraisal service is required before any runtime ingress. Whether Volition should additionally make those fields unforgeable is a separate owner/release decision. This harness does not alter Volition or claim to close that wider gap.

**Release gates remain open:** independent exact-head hostile review, host-owned provenance binding, current-consent and principal verification where applicable, CI readback, and ownership/CLA adjudication. A green test is not proof that an installed model uses either component.
