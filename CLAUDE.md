<!-- GSD:project-start source:PROJECT.md -->
## Project

**Browser Workflow Memory**

Research prototype for a workflow-memory layer on top of a browser-use agent. The system targets repeated tasks on specific websites, stores reusable successful workflows, and later reuses them to reduce redundant exploration while preserving task success.

**Core Value:** Repeated browser tasks on the same site should become measurably more efficient after one successful run.

### Constraints

- **Scope**: Narrow repeated-task workflows on specific sites only — keeps the hypothesis measurable.
- **Product framing**: Research prototype, not production software — avoids overclaiming.
- **Evaluation**: Must include baseline vs memory comparison — otherwise the memory layer claim is not demonstrated.
- **Deliverables**: Needs README, screencast, and REFLECTION.md — final repo must support submission packaging.
- **Architecture**: Memory layer should stay decoupled from browser runtime — helps attribute failures correctly.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
