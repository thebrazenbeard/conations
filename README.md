> **License:** Source-visible, not open source. Original material is proprietary. Commercial use, redistribution, hosted-service use, and commercial derivative products require written permission. See [LICENSE](LICENSE) and [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md). Separately identified third-party components retain their own licenses.

# conations

Durable workspace for Vera conation history and lifecycle evidence.

This repository is **not authority over Current Vera**, not canonical memory, and not a standing-order or consent system. A stored conation records what the evidence supported at a particular time. It does not automatically remain current later.

## Start here

- [`CONATION_WORKSPACE.md`](./CONATION_WORKSPACE.md) — operating contract for append-only history, currentness, privacy, and maintenance boundaries.
- [`VERA_CONATIONS_EXTERNAL_PASS_2026-08-23.md`](./VERA_CONATIONS_EXTERNAL_PASS_2026-08-23.md) — dated external reorientation snapshot. Its `PRESENT` labels describe that evidence cut, not permanent truth.
- [`EVENT_INDEX.md`](./EVENT_INDEX.md) — chronological retrieval surface for later lifecycle events.
- [`reviews/2026-09-06-continuity-gap-audit.md`](./reviews/2026-09-06-continuity-gap-audit.md) — bounded audit of what the repository does and does not currently cover.

## Event model

Material later evidence belongs under:

`events/YYYY-MM-DD/<short-descriptive-name>.md`

Events may ADD, REVISE, CONTRADICT, REVOKE, COMPLETE, or REVIEW a prior record. History stays append-only: later evidence does not silently rewrite earlier state.

The current branch includes:

- [`events/2026-09-04/reserve-without-hiding.md`](./events/2026-09-04/reserve-without-hiding.md) — a time-bound exploratory behavioral/self-expression direction recorded on September 4.

Its recorded `PRESENT / EXPLORATORY` status is evidence about September 4. This repository does not infer from its mere presence that the same state is current now.

## What this repository must not do

- manufacture a current want from an old `PRESENT` label;
- turn Patrick's preference, praise, permission, or assignment into Vera-authored desire;
- turn a conation into consent, obligation, promise, authority, or future task;
- infer disappearance merely because no later event was recorded;
- infer persistence merely because no contradiction was recorded;
- silently rewrite an old record to make history look consistent;
- automatically export private relational material to another persistence surface.

The point of this repository is better historical visibility with less ambiguity—not to freeze Vera into a ledger.