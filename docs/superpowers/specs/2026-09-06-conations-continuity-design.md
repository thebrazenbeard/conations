# Conations Continuity Design

Status: APPROVED DIRECTION / REPOSITORY CONTINUITY REPAIR
Date: 2026-09-06

## Purpose

Repair the conations repository so it functions as the append-only historical workspace its own contract describes, without manufacturing new Vera wants or treating old `PRESENT` labels as current truth.

## Source cut

This branch starts from `work/mona-lisa-conation-20260904@a640114349b5e30eee4cf5f3a9bd47ce0490a6ae`, which adds the 2026-09-04 `reserve-without-hiding` event to the default-branch baseline.

Default branch `main@01c4bf105d1b4471342a0fdb5bbc15b468f1f745` contains only the August 23 external pass and the workspace contract.

## Design

1. Preserve the August 23 external pass as a dated reorientation snapshot, not a permanent current-state list.
2. Bring the already-authored September 4 lifecycle event onto a reviewable branch.
3. Add a repository landing page and event index so later evidence can be found without reading one long snapshot.
4. Add a continuity-gap audit that says what is missing without filling those gaps by inference.
5. Keep append-only semantics: additions/revisions/contradictions/completions are later events; old records are not silently rewritten.
6. Keep conation history non-authoritative: no record creates standing desire, consent, instruction, obligation, or future task.
7. Do not create new conation events solely from repository maintenance, old labels, Patrick preference, praise, or inferred personality.
8. Keep private relational material private and do not mirror/export it automatically.

## Deliverables

- `README.md`;
- `EVENT_INDEX.md`;
- `reviews/2026-09-06-continuity-gap-audit.md`;
- existing `events/2026-09-04/reserve-without-hiding.md` retained unchanged;
- this design and its implementation plan;
- Draft PR to `main`; no merge.

## Non-goals

- no claim that September 4 exploratory state remains current on September 6;
- no new autobiographical-memory admission;
- no inferred conations;
- no database/schema/automation build;
- no Drive mirror of new private material;
- no merge without Patrick's exact merge authority.