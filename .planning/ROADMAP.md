# Roadmap: Browser Workflow Memory

## Overview

The project starts with a narrow browser-task harness and baseline agent execution, then adds a decoupled workflow-memory layer, evaluates whether memory improves repeated-task efficiency, and finishes by packaging the result into a credible test-task submission.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions if needed

- [ ] **Phase 1: Baseline Harness** - Establish the repeated-task environment, target sites, and no-memory execution flow.
- [ ] **Phase 2: Workflow Memory Layer** - Capture, retrieve, and apply reusable site-specific workflow memory.
- [ ] **Phase 3: Evaluation Loop** - Compare baseline and memory-assisted runs with concrete metrics and failure analysis.
- [ ] **Phase 4: Submission Packaging** - Finalize repository UX, demo path, and reflection artifacts for the test task.

## Phase Details

### Phase 1: Baseline Harness
**Goal**: Create a reproducible browser-use baseline for repeated tasks on one narrow site/task family with complete run tracing.
**Depends on**: Nothing (first phase)
**Requirements**: [TASK-01, TASK-02, TASK-03]
**Success Criteria** (what must be TRUE):
  1. User can run the baseline agent against at least one target site and one repeated task family.
  2. Each run emits artifacts showing task outcome, action sequence, and timing.
  3. The chosen benchmark scope is narrow enough that later memory reuse can be tested credibly.
**Plans**: 3 plans

Plans:
- [x] 01-01: Select runtime stack, target site, and benchmark task family
- [x] 01-02: Implement baseline execution entrypoint and tracing
- [ ] 01-03: Validate reproducibility and sample runs

### Phase 2: Workflow Memory Layer
**Goal**: Add a decoupled memory subsystem that stores and retrieves reusable successful workflows for repeated site-specific tasks.
**Depends on**: Phase 1
**Requirements**: [MEM-01, MEM-02, MEM-03, MEM-04, MEM-05]
**Success Criteria** (what must be TRUE):
  1. Successful runs produce memory artifacts with enough context to support reuse.
  2. Later runs can retrieve a relevant memory entry and apply it during execution.
  3. Logs make clear when memory was used, ignored, or rejected as mismatched.
  4. The agent can fall back to baseline behavior when memory is stale or not applicable.
**Plans**: 3 plans

Plans:
- [x] 02-01: Design memory schema and persistence boundary
- [ ] 02-02: Implement retrieval and execution guidance path
- [ ] 02-03: Add mismatch handling and observability

### Phase 3: Evaluation Loop
**Goal**: Measure whether workflow memory improves repeated-task efficiency without materially harming task success.
**Depends on**: Phase 2
**Requirements**: [EVAL-01, EVAL-02, EVAL-03]
**Success Criteria** (what must be TRUE):
  1. The same task suite can be run in baseline and memory-assisted modes.
  2. Results summarize success rate, action count, and run time per scenario.
  3. At least one honest failure case or brittleness pattern is documented.
**Plans**: 2 plans

Plans:
- [ ] 03-01: Build comparison runner and metrics aggregation
- [ ] 03-02: Execute experiments and analyze outcomes

### Phase 4: Submission Packaging
**Goal**: Turn the prototype and evidence into a clean submission with runnable instructions and demo-ready outputs.
**Depends on**: Phase 3
**Requirements**: [SHIP-01, SHIP-02]
**Success Criteria** (what must be TRUE):
  1. Repository exposes a one-command path for setup or demo execution.
  2. README explains scope, claims, sources, and limitations clearly.
  3. The project has enough material for screencast and REFLECTION.md without reverse-engineering the codebase.
**Plans**: 2 plans

Plans:
- [ ] 04-01: Finalize repo UX and documentation
- [ ] 04-02: Prepare demo narrative and reflection inputs

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Baseline Harness | 1/3 | In progress | - |
| 2. Workflow Memory Layer | 1/3 | In progress | - |
| 3. Evaluation Loop | 0/2 | Not started | - |
| 4. Submission Packaging | 0/2 | Not started | - |
