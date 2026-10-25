# Conation history — read-only consumer contract V1

`conation_manifest.py export` produces an opt-in, local JSON projection from
the repository's indexed Markdown lifecycle events. Nothing is sent to a host,
model, database, or another repo by this tool. It validates index membership,
event header fields, provenance section presence, path dates, UTF-8, and
unexpected symlinks; it cannot prove the truth or authorship of source prose.

Index membership requires a *standalone Markdown link line* to the event file.
Path-like prose, images, blockquotes, fenced/indented code, and inline code do
not count. Raw HTML markup outside fenced code (including comments and custom
block tags) is **unsupported and fails the whole index**, rather than being
partially parsed as membership. Backslash-escaped link-like text is literal
text, not an index entry. Reference-style and complex nested links are not
supported; use a simple `[label](./events/YYYY-MM-DD/name.md)` entry instead.

## JSON surface

The top-level keys are:

| Field | Meaning |
| --- | --- |
| `schema` | `conations.history.v1`, a source-control schema label |
| `currentness` | Always `history_only` |
| `effect_authority` | Always `none` |
| `activation` | Always `fresh_reappraisal_required` |
| `events[]` | Dated source metadata; **not** active drive signals |

Each default `events[]` entry has `event_date`, `event_type`,
`content_sha256`, and `status_currentness: historical_only`. The relative
`path` is omitted by default because a descriptive basename may reveal private
historical or relational context.
The digest covers the exact stored file **bytes**, including line endings. A
recorded label such as `PRESENT` describes the dated event; it is not current
state. `export --include-path`, `--include-subject`, and `--include-status`
work independently. Even a date/digest pair may permit linkage to another
copy of the same evidence. These are explicit local disclosure choices, not
licenses for remote replication or model training.

## Boundary for Meso-CRCT, Volition, and other consumers

Consumers who explicitly opt into event paths may use a path/digest as a
locator for review or evidence retrieval. They must not infer present salience, pleasure, valence, desire,
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

Default `export` failures disclose only fixed diagnostic categories, not
descriptive paths, private header values, or traceback causes. The public
`build_manifest()` API applies the same default error redaction, including
when `include_path=True`; this option never silently enables field diagnostics.
`export --include-diagnostics` and programmatic `include_diagnostics=True`
explicitly reveal fuller local validation error details; local `check` is
diagnostic by design. Such output is sensitive and must not be routed to a
model, Bus, analytics service, or external logger without separate authority.
Unexpected programming/runtime failures are not a promise of full metadata
privacy, and the SHA-256/content dates still allow correlation.
