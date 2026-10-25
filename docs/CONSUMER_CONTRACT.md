# Conation history — read-only consumer contract V1

`conation_manifest.py export` produces an opt-in, local JSON projection from
the repository's indexed Markdown lifecycle events. Nothing is sent to a host,
model, database, or another repo by this tool. It validates index membership,
event header fields, provenance section presence, path dates, UTF-8, and
unexpected symlinks; it cannot prove the truth or authorship of source prose.

## JSON surface

The top-level keys are:

| Field | Meaning |
| --- | --- |
| `schema` | `conations.history.v1`, a source-control schema label |
| `currentness` | Always `history_only` |
| `effect_authority` | Always `none` |
| `activation` | Always `fresh_reappraisal_required` |
| `events[]` | Dated source metadata; **not** active drive signals |

Each `events[]` entry has `path`, `event_date`, `event_type`,
`recorded_status`, `content_sha256`, and `status_currentness: historical_only`.
The digest covers the exact stored file **bytes**, including line endings. A
recorded label such as `PRESENT` describes the dated event; it is not current
state. `subject` is omitted unless the caller invokes `export
--include-subject`, which is an explicit disclosure choice, not a license for
remote replication or model training.

## Boundary for Meso-CRCT, Volition, and other consumers

Consumers may use an event path/digest as a locator for review or evidence
retrieval. They must not infer present salience, pleasure, valence, desire,
DriveKind, a normalized magnitude/confidence, behavioral authority, consent,
future task, or authorization from an old record. In particular, **no** direct
mapping from `recorded_status: PRESENT` to an active Volition `Signal` or
Meso-CRCT state is valid. Such state requires independently obtained *fresh*
evidence and a separate authorized decision path. This exporter supplies none.

Validation does not establish historical completeness, cryptographic author
authentication, semantics, active runtime installation, or independent
currentness. `EVENT_INDEX.md` is an explicit set of known indexed events, not a
guarantee that every relevant conversation was captured.

## Failure behavior

`check` and `export` exit nonzero if an indexed event is absent, an event file
is unindexed, the header is ambiguous/invalid, or a direct event file is a
symlink. A failure does **not** imply a desire is absent or revoked; it means
the checkout is unsuitable for this bounded machine projection until repaired.
