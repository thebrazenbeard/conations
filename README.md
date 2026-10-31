> **License:** Source-visible, not open source. Original material is proprietary. Commercial use, redistribution, hosted-service use, and commercial derivative products require written permission. See [LICENSE](LICENSE) and [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md). Separately identified third-party components retain their own licenses.

# Conations — historical intent and motivation evidence ledger

**An append-only, evidence-first pattern for recording the lifecycle of expressed conations without converting yesterday's record into today's desire, consent, or authority.**

Conations combines dated Markdown records, an event index, a standard-library Python validator/exporter, and a strict read-only consumer projection. It is intended for researchers and agent-runtime integrators who need to preserve *what was recorded, when, and with what provenance* while requiring a separate fresh appraisal before acting on it.

This is **not** a model, a desire detector, a general-purpose database service, an automatic memory system, or an authorization provider. The current checked-in history is project-specific; other systems can evaluate the documented pattern and code under the repository's license, but must adapt their own data, authoring rules, privacy policy, and currentness authority.

## Supported surfaces

| Surface | Current implementation | Boundary |
| --- | --- | --- |
| Dated lifecycle events | Markdown under `events/YYYY-MM-DD/<name>.md` with `ADD`, `REVISE`, `CONTRADICT`, `REVOKE`, `COMPLETE`, or `REVIEW` | A recorded state is historical evidence, not a current state |
| Index validation | `conation_manifest.py check` validates index membership, event headers, provenance presence, dates, UTF-8, and unexpected symlinks | Structural validation does not establish the truth or self-authorship of prose |
| Local historical export | `conation_manifest.py export` emits a deterministic JSON projection to standard output | No network upload or automatic downstream registration; dates/digests can still be correlating identifiers |
| Consumer boundary | `conation_history_context.py` parses and minimizes exported historical metadata | Never constructs an active want, task, permission, or model-drive signal |

The export contract carries `schema: conations.history.v1`, `currentness: history_only`, `effect_authority: none`, and `activation: fresh_reappraisal_required`. This is a **source-defined historical projection**, not proof of who authored an event or authorization to reuse it elsewhere. See [the consumer contract](docs/CONSUMER_CONTRACT.md) for supported input forms, rejection behavior, and field semantics.

## Use from a permitted source checkout

The tools use Python's standard library; there is no package installation, cloud service, API key, or model server prerequisite for these commands:

```bash
python conation_manifest.py check
python conation_manifest.py export
python -m unittest discover -s tests -v
```

For a Python consumer that needs only the minimized history metadata:

```python
import subprocess
from conation_history_context import parse_history_export

raw = subprocess.check_output(["python", "conation_manifest.py", "export"])
events = parse_history_export(raw)  # tuple of historical evidence records
```

This example stays local and read-only. A consuming host must independently decide whether the records may be retrieved, retained, or disclosed; the library does not activate present motivation or grant a capability. The example was exercised against this repository's indexed source data, not against a live agent runtime.

### Privacy defaults and opt-ins

The default export includes dated lifecycle types and raw-byte SHA-256 content digests, while omitting descriptive event paths, subjects, and recorded status. Explicit `--include-path`, `--include-subject`, and `--include-status` options independently permit those extra fields. These options are **disclosure controls**, not anonymization guarantees.

Default export-validation errors use fixed categories rather than leaking event paths and field values. Richer local diagnostics require `--include-diagnostics`; `check` is explicitly diagnostic and may also expose sensitive local context. Do not automatically forward opt-in exports or diagnostics to another model, provider, database, or public channel. `parse_history_export` / `historical_context` intentionally discard optional private fields from their minimized consumer view.

## Historical state is not active authority

The event model is append-only: later evidence may revise, contradict, revoke, complete, or review a record, but it must not silently rewrite the original. A missing later event does **not** prove either persistence or disappearance.

This repository must not:

- infer a present want from an old `PRESENT` label;
- treat another person's preference, praise, instruction, or permission as the agent's self-authored desire;
- convert a historical conation into consent, obligation, a standing order, a task, or effect authority;
- infer a real person's or model's private experience, motivation, or identity from the ledger alone;
- turn source consistency or a successful parser result into independent confirmation of authorship or truth;
- replicate private relational history onto another surface without separate permission.

**Fresh, independently governed reappraisal is required before any runtime uses history as context for new decisions.** A separate volition or action system may read authorized historical metadata, but it cannot inherit permission or currentness from this repository.

## This repository's included history

The tracked records currently describe a specific agent's historical research and are **not a generic fixture dataset**. The dated labels below describe evidence cuts, not claims of current state:

- [Workspace operating contract](CONATION_WORKSPACE.md) — append-only records, privacy, maintenance, and self-authorship boundaries.
- [Event index](EVENT_INDEX.md) — chronological retrieval surface.
- [Historical external reorientation snapshot](VERA_CONATIONS_EXTERNAL_PASS_2026-08-23.md) — `PRESENT` and other labels belong to the August 2026 snapshot.
- [Example dated event](events/2026-09-04/reserve-without-hiding.md) — an exploratory record at its original event date.
- [Read-only consumer contract](docs/CONSUMER_CONTRACT.md) — exact JSON schema and privacy-minimizing projection.
- [Continuity-gap review](reviews/2026-09-06-continuity-gap-audit.md) — what the evidence does and does not cover.

For historical project context, retain those source documents rather than substituting an inferred current persona or status. A green unit test establishes the tool's tested source behavior, **not** live memory integration, consciousness, consent, or effect authorization.
