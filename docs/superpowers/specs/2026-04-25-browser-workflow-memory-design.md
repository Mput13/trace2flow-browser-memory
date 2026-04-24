# Browser Workflow Memory Design

## Summary

This project is a research prototype for a workflow-memory layer on top of a real `browser-use` runtime. The system executes repeated browser tasks on concrete sites, analyzes the baseline trajectory, synthesizes an optimized workflow, reruns the task with structured hints, and admits the resulting memory only if the optimized rerun is verified and measurably better.

The prototype is designed around two reproducible public benchmark contexts:
- `Recreation.gov` as a public, no-login site
- public MAI schedule pages on `mai.ru` as a public, no-login site

An additional private exploratory context may be used for development or demo purposes:
- `my.mai.ru` with session reuse and optional credential login

The central claim is narrow on purpose: exact workflow reuse on the same site and within the same task family should reduce unnecessary exploration, loops, and time-to-completion without reducing task success.

## Goals

- Build a reproducible browser task pipeline around the real `browser-use` runtime.
- Capture rich run artifacts from the first baseline pass.
- Analyze trajectories and synthesize an optimized workflow representation rather than storing only raw traces.
- Reuse admitted memory on future runs through structured hint packets.
- Compare baseline, optimized rerun, and fresh memory-assisted runs with stable metrics.
- Support multiple site adapters through one shared pipeline, with public benchmarks as the default reproducible path.
- Expose the system through a CLI-first interface that can later be orchestrated by an external agent shell.

## Non-Goals

- Replacing `browser-use` with a custom browser agent runtime.
- Building a universal cross-site memory system.
- Solving general web autonomy or open-web planning.
- Making the external shell agent the source of truth for execution logic.
- Shipping a polished UI application.
- Using embeddings or semantic retrieval as the main retrieval mechanism in `v1`.

## Product Boundary

The system is not an autonomous agent platform. It is a workflow-memory system around a browser agent runtime. The browser runtime remains responsible for acting in the browser. The memory system is responsible for:
- running controlled experiments,
- judging results,
- analyzing traces,
- synthesizing optimized workflows,
- rerunning with memory hints,
- and deciding whether a memory object should be stored.

The primary `v1` behavior is exact workflow reuse:
- same site,
- same task family,
- similar input shape,
- same expected output type.

Site-scoped family reuse on the same site is allowed as a stretch goal. Cross-site reuse is explicitly outside `v1`.

## Supported Sites And Task Families

### Recreation.gov

Primary task family:
- Search for a campground or campsite using structured filters, open the relevant result, and extract a structured answer from the result details.

Typical task inputs:
- location or campground query
- dates
- equipment type
- pet policy
- RV length or similar constraints

Typical output:
- structured result with chosen item, key restrictions, and availability-related details

### Public MAI Schedule

Primary task family:
- Find the schedule for a given input on the public MAI schedule pages and extract a structured schedule answer.

Typical task inputs:
- group, date, day, week, or similar schedule parameters

Typical output:
- structured result with class time, subject, room, teacher, and date context

Primary benchmark entrypoint:
- `https://mai.ru/education/studies/schedule/groups.php`

### my.mai.ru (Exploratory Only)

Authentication modes:
- session reuse as the default operator-friendly mode
- credential login from environment/config as an optional full-run mode

This context is explicitly non-blocking for external reproducibility and is not part of the core benchmark claim.

## Core Design Decisions

- `browser-use` remains the real execution engine.
- The project uses a Python core pipeline and not a shell-agent-centric architecture.
- Analysis and optimization are hybrid:
  - Python computes deterministic features, metrics, and normalized artifacts.
  - LLM-based judging and optimization operate on a structured packet rather than raw logs alone.
- Optimization is a single LLM pass with one structured response:
  - `analysis`
  - `optimized_workflow`
  - `human_summary`
- The external shell agent is an orchestrator adapter and not the owner of business logic.
- Memory admission is strict: no optimized rerun, no memory.
- The storage model is split:
  - raw artifacts on disk as JSON and related files
  - indexed entities and metrics in SQLite
- Configuration is centralized in `config/project.yaml`, with secrets in `.env`.
- The first-line README track tag for submission is `Track: C+D`.

## System Architecture

The system is divided into five layers.

### 1. Execution Core

The execution core provides:
- CLI entrypoints
- runtime configuration loading
- browser session/profile handling
- `browser-use` invocation
- artifact capture hooks

Responsibilities:
- accept a job definition
- prepare the session for the chosen site
- run baseline or memory-assisted execution
- capture raw action history, timing, outcome metadata, and optional screenshots

### 2. Site Adapter Layer

Each site adapter contains only site-specific knowledge.

Responsibilities:
- define supported task families
- transform user/task input into a task prompt or runner payload
- prepare authentication/bootstrap behavior
- define rule-based success checks
- provide page-state hints and task signature fields

The adapter does not own:
- memory retrieval
- metrics logic
- rerun comparison
- admission logic
- batch evaluation logic

### 3. Analysis Pipeline

The analysis pipeline transforms a raw run into a structured object suitable for judgment and optimization.

Responsibilities:
- normalize actions and observations
- compute page-state fingerprints
- detect loops and retries with deterministic rules
- compute metrics
- run rule-based verification
- run a WebJudge-inspired LLM verification pass when deterministic checks are insufficient
- assemble the optimization input packet

### 4. Memory Layer

The memory layer manages memory objects and retrieval.

Responsibilities:
- persist admitted memory entries
- retrieve candidate entries for new tasks
- score candidates within the same site and task family
- build the hint packet for reruns or memory-assisted fresh runs
- perform admission comparison and persistence

### 5. Evaluation Layer

The evaluation layer runs repeated experiments and produces aggregate outputs.

Responsibilities:
- run the seed baseline
- run the optimize cycle
- run fresh memory-assisted tasks
- parallelize independent jobs
- aggregate metrics
- produce per-scenario and per-site summaries
- preserve failure cases and brittleness evidence

## Generic Pipeline Vs Site Adapters

The boundary between shared logic and site-specific logic is strict.

### Site Adapter Responsibilities

- task family definitions
- input parsing and task signature fields
- authentication/bootstrap
- page-state hints specific to the site
- rule-based success checks
- optional structured extraction helpers for final answers

### Generic Pipeline Responsibilities

- run orchestration
- artifact capture and persistence
- trace normalization
- fingerprinting
- loop and retry detection
- verifier orchestration
- optimization-pass orchestration
- rerun with memory hints
- comparison and admission
- SQLite indexing
- batch evaluation and reporting

This separation is required so the project remains one memory system across multiple sites rather than two unrelated site scripts.

## End-To-End Execution Flow

One optimization job follows this exact sequence:

1. Receive `site`, `task_family`, `task_input`, and `run_mode`.
2. Load the site adapter and runtime config.
3. Prepare browser session state:
   - public mode for `Recreation.gov` and public MAI schedule pages
   - session reuse or credential login for `my.mai.ru`
4. Run a baseline task through `browser-use`.
5. Persist raw artifacts:
   - task input
   - action history
   - elapsed time
   - screenshots or metadata if enabled
   - final raw output
6. Normalize the run into a structured packet.
7. Compute deterministic process metrics:
   - `action_count`
   - `elapsed_time`
   - `loop_count`
   - `retry_count`
8. Run verification:
   - first rule-based
   - then a WebJudge-inspired LLM outcome judgment if needed
9. Send the structured packet to a single optimization pass.
10. Receive:
   - structured `analysis`
   - structured `optimized_workflow`
   - human-readable optimization summary
   - structured rerun hint packet
11. Run the optimized rerun with the hint packet.
12. Recompute metrics and rerun verification.
13. Compare baseline and optimized rerun.
14. Admit memory only if rerun:
   - passes verification,
   - is not worse on success,
   - and improves at least one key process metric beyond the threshold.
15. Persist admitted memory and evaluation outputs.

## Run Modes

The CLI and orchestration layer must support four modes.

### `baseline`

Run a single task without memory and persist artifacts.

Use cases:
- first-run debugging
- smoke checks
- generating a seed trace for optimization

### `optimize`

Run the full cycle:
- baseline
- judge
- analyze
- optimize
- rerun
- compare
- admit or reject

This is the main mode for building memory.

### `memory-run`

Run a task using already admitted memory.

Use cases:
- demonstrating reuse
- fresh task evaluation
- user-facing orchestrated execution

### `eval-batch`

Run a suite of independent jobs for one or more sites with optional parallel execution at the job level.

Constraints:
- each individual browser workflow stays sequential
- only independent jobs are parallelized

Jobs are independent only if they do not share mutable runtime state:
- separate artifact directories
- separate run identifiers
- separate browser profiles or session state

Authenticated jobs against the same account should run sequentially by default.

## Agent Tool Surface

The CLI is the stable tool contract for external shell agents.

An external agent does not call internal Python functions directly. It invokes CLI commands through its shell or command-execution tool.

Minimum tool surface:
- `workflow-memory baseline --site ... --task-family ... --input ...`
- `workflow-memory optimize --site ... --task-family ... --input ...`
- `workflow-memory memory-run --site ... --task-family ... --input ...`
- `workflow-memory eval-batch --suite ...`

This is how the project satisfies the requirement that the final agent genuinely uses tools. The external agent uses the CLI as its tool interface, while the CLI delegates into the shared pipeline.

## Data Model

### Task Definition

A task definition describes:
- site
- task family
- input schema
- expected output schema
- success-check strategy
- adapter-specific page hints

### Task Signature

The task signature is a compact retrieval key built from:
- `site`
- `task_family`
- normalized input fields relevant for exact reuse

It is not an embedding. It is an interpretable structured key with lightweight scoring features.

### Run Artifact

Each run artifact should contain:
- run identifier
- site
- task family
- task input
- run mode
- timestamps
- normalized action list
- raw browser-use result data
- page-state sequence
- rule-based verifier output
- optional LLM verifier output
- metrics
- links to related files on disk

### Memory Entry

Each admitted memory entry contains:
- memory identifier
- site
- task family
- task signature
- input features used for retrieval scoring
- workflow summary
- likely path
- page hints
- success cues
- mismatch signals
- optimization notes
- source baseline run id
- optimized rerun id
- admission result metadata
- links to underlying raw artifacts

The memory entry is the reusable object. Raw traces remain attached for audit and debugging.

## Storage Strategy

### Config And Secrets

Project configuration lives in:
- `config/project.yaml`

Secrets live in:
- `.env`

`config/project.yaml` must define:
- model names for verifier and optimization pass
- artifact root paths
- SQLite path
- browser profile defaults
- pinned runtime dependency versions
- admission thresholds
- retrieval scoring weights
- parallelism defaults

Default model choices for `v1`:
- `judge_model: gpt-4.1-mini`
- `optimize_model: gpt-4.1`

These defaults are chosen for cost/performance balance and remain overridable in config. OpenAI documents describe GPT-4.1 mini as a smaller, faster GPT-4.1 model and GPT-4.1 as the smarter non-reasoning model in the same family.

Runtime dependencies such as `browser-use` and Playwright must be pinned in the project dependency lockfile and mirrored in `config/project.yaml` or generated runtime metadata for reproducible evaluation.

### File-Based Artifacts

Store raw execution artifacts on disk:
- normalized run JSON
- raw trace JSON
- optional screenshots
- human-readable optimization summaries
- evaluation report exports

Why:
- easier debugging
- direct inspection during research
- readable inputs for README, reflection, and screencast preparation

Canonical artifact layout:
- `artifacts/runs/<run_id>/trace.json`
- `artifacts/runs/<run_id>/normalized.json`
- `artifacts/runs/<run_id>/result.json`
- `artifacts/runs/<run_id>/verifier.json`
- `artifacts/runs/<run_id>/screenshots/`
- `artifacts/optimizations/<run_id>/optimization.json`
- `artifacts/optimizations/<run_id>/summary.md`
- `artifacts/evals/<eval_id>/summary.json`
- `artifacts/evals/<eval_id>/report.md`

### SQLite Index

Store structured entities in SQLite:
- task definitions
- runs
- memory entries
- retrieval decisions
- aggregate metrics
- evaluation jobs and summaries

Why:
- easy filtering and comparisons
- reliable local storage
- simple admission and reporting queries

Canonical SQLite location:
- `data/workflow_memory.sqlite`

## Page-State Fingerprinting And Loop Detection

### Page-State Representation

Each page state is represented by:
- current URL
- page title
- a compact fingerprint derived from visible text and key page labels

The fingerprint should favor:
- stable visible headings
- key buttons or links
- important labels around the current interaction area

It should avoid overfitting to noisy or highly variable page content.

Matching semantics:
- `same page state`: identical normalized URL path, identical title, identical fingerprint hash
- `near-identical page state`: same normalized domain/path family and fingerprint similarity above a configurable threshold

Default `near_identical_threshold`:
- `0.80`

### Loop Detection

Loop and retry counting are deterministic in Python.

Signals include:
- revisiting the same or near-identical page state repeatedly
- repeating the same action pattern without progress
- returning to the same workflow region after an unsuccessful branch
- repeating the same search, click, or submit sequence

The LLM analyzer may later reinterpret these as wasted exploration or reasonable recovery, but the numeric loop/retry metrics come from deterministic rules.

## Verification Strategy

Verification is hybrid and layered.

### Rule-Based Verification

Used whenever a site/task family allows deterministic success checks.

Examples:
- expected fields extracted
- schedule entries found for the chosen date
- result card opened and required details captured

### WebJudge-Inspired LLM Verification

Used when deterministic checks are incomplete or ambiguous.

Inputs may include:
- task description
- action history
- structured output
- selected screenshots or page summaries

The LLM verifier is a second-layer outcome judge, not the source of process metrics.

The project does not claim to fully reproduce the original WebJudge benchmark protocol. It borrows the high-level idea of LLM-as-judge over task context, action history, and selected visual or page-state evidence.

## Analysis And Optimization

The optimization pass does not read raw browser history only. It consumes a structured packet prepared by Python.

### Optimization Input Packet

- task context
- site and task family
- page-state sequence
- action sequence
- verifier outputs
- metrics
- loop/retry annotations
- optional screenshots or summaries

### Single Optimization Pass Contract

The pipeline issues one LLM call for optimization. That call returns three logical outputs in one structured response:
- `analysis`
- `optimized_workflow`
- `human_summary`

#### Analysis

Contains:
- inefficiencies in baseline behavior
- identified wasted exploration or loops
- reasoning for the proposed optimized path
- known uncertainty or brittleness points

#### Machine-Readable Workflow Object

Contains:
- optimized workflow summary
- likely path steps
- page/section hints
- success cues
- mismatch signals
- optimization notes

This object is used by the pipeline for rerun and future retrieval.

#### Human-Readable Summary

Contains:
- what was inefficient in the baseline
- what was changed in the optimized workflow
- why the optimized path should be better
- where brittleness may still remain

This view is for debugging, reporting, and final submission materials.

## Retrieval Strategy

Retrieval is deliberately simple and interpretable in `v1`.

### Step 1: Hard Filter

Candidates must match:
- same `site`
- same `task_family`

### Step 2: Lightweight Scoring

Within the filtered set, candidates are scored by a weighted field-by-field similarity function:
- exact match for categorical fields such as `task_family` subtypes
- set overlap or Jaccard similarity for filter collections
- bucketed overlap or tolerance scoring for numeric and date-like fields
- normalized string similarity for free-text query fields
- optional adapter-provided contextual cues with explicit weights

`v1` does not depend on embeddings. The retrieval method should stay easy to inspect and explain.

If a field is marked critical by the adapter, a mismatch on that field may zero out the candidate regardless of the aggregate score.

## Hint Packet Design

Memory affects execution through a structured hint packet and not through hidden runtime mutation.

Each hint packet should include:
- task goal restatement
- likely path
- page or section hints
- success cues
- mismatch signals

This is the only intended memory influence path for `v1`.

## Admission Policy

Memory is admitted only after a validated optimized rerun.

Admission criteria:
- optimized rerun passes verification
- optimized rerun does not reduce success quality relative to baseline
- optimized rerun improves at least one of:
  - `action_count`
  - `elapsed_time`
  - `loop/retry_count`

Initial `v1` threshold:
- 10% improvement on at least one key metric with no success regression

The exact threshold value is configured in `config/project.yaml`.

Default keys:
- `admission.min_relative_improvement: 0.10`
- `admission.require_no_success_regression: true`

The default behavior must stay conservative to avoid storing low-quality memory.

## Error Handling And Partial Runs

Every run must persist an artifact directory even when execution fails mid-run.

Canonical run statuses:
- `succeeded`
- `failed_execution`
- `failed_verification`
- `failed_optimization`
- `failed_rerun`

Failure metadata must include:
- `failure_stage`
- `error_summary`
- `partial_artifacts_written`

This is required for later failure analysis, especially on brittle or authenticated flows.

## Evaluation Design

The evaluation loop for each benchmark context contains three stages.

### Stage 1: Seed Baseline

Run a no-memory pass to produce the initial trace and metrics.

### Stage 2: Optimized Rerun

Run the optimize cycle and determine whether the optimized path deserves admission.

### Stage 3: Fresh Memory-Assisted Runs

Run one or more new tasks in the same site/task family with admitted memory to show actual reuse rather than only trace compression.

### Parallelism

Parallel execution is supported only across independent jobs. A single browser workflow remains sequential.

## Testing Strategy

Testing is split into four levels.

### Unit Tests

Must cover:
- task signature building
- retrieval scoring
- page-state fingerprinting
- loop detection
- admission policy
- hint packet construction

### Integration Tests

Must cover:
- adapter contract behavior
- SQLite persistence
- artifact writing
- verifier orchestration
- optimizer input/output handling

### Smoke Tests

Must cover:
- one public-site scenario on `Recreation.gov`
- one public MAI schedule scenario

Smoke tests are allowed to be narrower than the evaluation suite but must prove end-to-end viability.

### Evaluation Tests

Must cover:
- baseline versus optimized rerun
- fresh memory-assisted execution
- at least one recorded brittleness or failure case

## Development Order

Implementation should proceed in this order:

1. Baseline execution harness and artifact capture
2. Site adapter interfaces and first concrete adapters
3. Structured run normalization, fingerprinting, and metrics
4. Verification layer
5. Analyzer and optimizer integration
6. Memory storage, retrieval, and admission
7. Evaluation batch runner and reporting
8. Agent adapter/orchestration interface
9. Final packaging for README, demo, and reflection

This order is intentional. It preserves debuggability and ensures the memory layer is built on observable execution rather than on speculative abstractions.

Step 8 specifically means exposing the CLI as a stable tool surface for external shell agents. It does not move execution logic out of the Python core.

## Future Development

Possible post-`v1` extensions:
- site-scoped family reuse beyond exact workflow matching
- stale-memory invalidation heuristics
- richer page-state comparison
- multiple orchestrator adapters
- broader benchmark coverage
- cross-site generalization experiments
- private authenticated exploratory adapters such as `my.mai.ru`

None of these should weaken or delay the `v1` claim.

## Risks And Failure Modes

The project should explicitly preserve evidence of the following risks:
- site UI changes make prior memory stale
- retrieval selects a plausible but misleading memory entry
- rule-based success checks are incomplete
- authenticated flows are less stable than public flows
- optimized hints overfit to one exact page state

These are not embarrassments. They are required parts of the research story and should appear in evaluation outputs and reflection materials.

## Deliverables Alignment

The architecture must support the test-task deliverables directly.

- `README` first line: `Track: C+D`

- `README`: runnable entrypoint, architecture summary, benchmark setup, and results
- `REFLECTION.md`: failure cases, tradeoffs, and next steps
- `screencast`: baseline versus memory-assisted execution
- repository structure: one-command setup or demo path

The design therefore prioritizes inspectability and reproducibility over breadth.
