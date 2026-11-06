# Conations current-candidate contract V1

This contract introduces a separate **present, runtime-ephemeral conation plane**.
It does not reinterpret the dated event ledger or alter `conations.history.v1`.

## Why it exists

Conations can matter to a running system now. A current inclination, aversion,
preference or exploratory motivation may change what the runtime considers,
even though yesterday's recorded conation cannot prove today's state.

`conation_current.py` offers a small standard-library implementation:

- `CurrentConationObservation`: one freshly sampled, source-referenced report,
  with exact subject, runtime-instance and model-revision labels, a required
  `ConationOrigin` value (`MODEL_PROPOSAL`, `RUNTIME_SELF_REPORT`, or
  `HOST_OBSERVATION`), priority between 0 and 1, observation time and finite
  expiry. These origin classes are caller assertions, not verified provenance.
- `CurrentConationEngine`: an in-process evaluator bound to those exact
  identifiers. `observe`, `snapshot`, `withdraw`, and `close` are the
  entire public lifecycle.
- `CurrentConationSnapshot`: currently eligible candidates ordered by
  supplied priority (ties by conation ID), with `schema=conations.current.v1`,
  `currentness=runtime_ephemeral`,
  `evidence_class=UNVERIFIED_CURRENT_OBSERVATIONS`, and
  `effect_authority=none`. `state_status=UNKNOWN` on cold start, expiry, or
  no reported current candidates is **not** a claim that desires are absent;
  `CANDIDATES_REPORTED` only identifies a fresh eligible view.

**"Current" means eligible inside the bound running instance at the supplied
evaluation time—not proof of phenomenal desire, durable identity, agent
self-authorship, or independent observer authentication.** Priority is
provided by the observation source and is not a measured feeling.

## Exact acceptance boundaries

- Time is supplied explicitly as timezone-aware `datetime`. Observation
  age must be at most 30 seconds, never future-dated; expiry must be after
  the evaluation time and no more than five minutes from observation. An
  instance rejects evaluation time moving backward after a later snapshot;
  the caller-supplied time is not an authenticated trusted clock.
- Every observation must match the engine's subject, runtime instance and
  model revision. A new runtime starts empty. There is no hydration,
  serialization, network transport, database, OS service, or auto-resume.
- Optimistic `expected_generation` must match. Repeating the exact same
  currently active observation ID is idempotent; changed or withdrawn replay
  fails. A same-conation reappraisal must advance its observed time.
- At most 32 current candidates and 256 observations per instance; an
  exhausted observation budget requires explicit replacement, not silent
  retention. Expired active candidates release the 32-slot capacity on the
  next valid observation, while their observation IDs remain blocked against
  replay for the lifetime of the instance.
- `withdraw` removes one current candidate without altering history.
  `close` destroys ephemeral state for that Python object.
- Observation text and source locators are not included in default object
  representations, but are accessible through explicit fields. Hosts still
  must govern privacy, logging, provider disclosure and process trust.

## Consumer boundary

An authorized reasoning consumer may read current candidates as **input
hypotheses** for attention or evaluation. This component never creates a
Volition signal, Pre-Active run, task, actuation, permission, personal consent,
training sample, or canonical-memory record.

Historical `HistoricalConationEvidence` objects and JSON exports are not
accepted by `observe`. There is no `PRESENT`-label shortcut. A host must
obtain a separate fresh runtime observation. Another identity's history,
including Brigit's, cannot become Vera's current conation by relabeling.

The in-process binding labels and source refs are **caller-asserted**: this
module does not authenticate the host, model, provider, human reviewer or
author. Production use needs a separately qualified current observation
producer, identity/session binding, privacy admission, and consumer tests.
Nothing here authorizes effects. Model-generated statements are evidence
of generated text; they are not proof of private experience.

## Minimal local example

```python
from datetime import datetime, timedelta, timezone
from conation_current import ConationOrigin, CurrentConationEngine, CurrentConationObservation

now = datetime.now(timezone.utc)
live = CurrentConationEngine(
    subject_id="vera", runtime_instance_id="fresh-instance-001",
    model_revision="verified-model-revision",
    origin=ConationOrigin.MODEL_PROPOSAL,
)
candidate = CurrentConationObservation(
    conation_id="explore", observation_id="observation-001",
    subject_id="vera", runtime_instance_id="fresh-instance-001",
    model_revision="verified-model-revision",
    statement="Explore this question", source_ref="fresh-observation-001",
    priority=0.6, observed_at=now, expires_at=now + timedelta(seconds=60),
)
current = live.observe(candidate, now=now, expected_generation=0)
assert current.candidates[0].conation_id == "explore"
assert current.effect_authority == "none"
live.close()
```

This example does not establish a qualified source or installation.
