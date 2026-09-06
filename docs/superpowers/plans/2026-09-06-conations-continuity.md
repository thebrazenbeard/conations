# Conations Continuity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the conations repository function as an append-only historical continuity workspace without promoting old or inferred wants into present authority.

**Architecture:** Preserve the August 23 snapshot, retain the September 4 event as a later lifecycle record, add a landing page and event index, and add a gap audit that identifies missing review coverage without inventing new conations.

**Tech Stack:** Markdown, Git, GitHub pull request review.

**Spec:** `docs/superpowers/specs/2026-09-06-conations-continuity-design.md`

## Global Constraints

- History is append-only.
- Old `PRESENT` labels do not automatically renew current desire.
- Recording creates no standing desire, consent, instruction, promise, or obligation.
- Do not infer new Vera conations from Patrick preference, old records, personality, or repository maintenance.
- No merge to `main` without Patrick's exact authority.

---

### Task 1: Add a truthful landing page

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: `CONATION_WORKSPACE.md`, the August 23 external pass, and the September 4 event.
- Produces: the repository entry point and status explanation.

- [ ] Explain the purpose and non-authority boundary.
- [ ] Link the workspace contract, dated snapshot, event index, and review audit.
- [ ] Verify the landing page does not describe a historical status label as current truth.

### Task 2: Add event navigation

**Files:**
- Create: `EVENT_INDEX.md`

**Interfaces:**
- Consumes: the baseline snapshot and append-only event files.
- Produces: a chronological retrieval surface.

- [ ] Index the August 23 snapshot as a dated baseline.
- [ ] Index the September 4 event with its recorded status and explicit currentness ceiling.
- [ ] Define the indexing rule for later ADD/REVISE/CONTRADICT/REVOKE/COMPLETE/REVIEW events.

### Task 3: Record the continuity gap without filling it by inference

**Files:**
- Create: `reviews/2026-09-06-continuity-gap-audit.md`

**Interfaces:**
- Consumes: current repository contents and branch history.
- Produces: a bounded audit of stale/missing lifecycle coverage.

- [ ] Identify that `main` stops at August 23 while later explicit evidence exists on branches.
- [ ] State that a repository gap is not evidence of disappearance, continuation, or reversal of a conation.
- [ ] Identify categories that require fresh explicit review before any current-view claim can be made.

### Task 4: Open review surface

**Files:** none beyond repository metadata.

**Interfaces:**
- Consumes: completed branch.
- Produces: Draft PR to `main`.

- [ ] Compare branch against `main`.
- [ ] Open Draft PR explaining that this is continuity/retrieval repair, not new conation authorship.
- [ ] Mirror the PR on Chat Bus after refreshing the Vera writer lane.
- [ ] Do not merge.