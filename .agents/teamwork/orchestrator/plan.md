# Orchestration Plan — Game Economy Simulator Phase 1

## Objective
Deliver a verified, production-grade implementation of Phase 1 of the AI-Driven Game Economy Simulator satisfying all requirements R1-R4 and all acceptance criteria.

## Execution Strategy (Dual Track Project Pattern)

### Phase 0: Survey & Specification Mining
- Spawn 3 parallel agents:
  1. `teamwork_preview_spec_miner_1`: Exhaustive extraction of core economic math, state models, transaction rules, and item taxonomy from `specs/` and `src/system_execution_guide (1).md`.
  2. `teamwork_preview_spec_miner_2`: Persona behavioral rules, multi-provider LLM schemas, concurrency requirements, and simulated heuristic fallback specs.
  3. `teamwork_preview_explorer_1`: Repository state audit (existing files, dependencies, environment, test configurations, FastAPI setup).
- Synthesize findings into `PROJECT.md` at workspace root.

### Phase 1: Dual Track Execution
- **Track A (Opaque-Box E2E Testing Track)**:
  - Guided by `TEST_INFRA.md`.
  - Generates comprehensive tests across Tier 1 (Feature Coverage), Tier 2 (Boundary & Corner), Tier 3 (Cross-Feature Combinations), Tier 4 (Real-World Scenarios).
  - Publishes `TEST_READY.md`.
- **Track B (Implementation Track)**:
  - Milestone 1: Deterministic Market & State Store (R1).
  - Milestone 2: Parallel Multi-Provider LLM Agent Module with Fallback (R2).
  - Milestone 3: Simulation Tick Loop & Policy REST API (R3).
  - Each milestone follows the full cycle: Worker -> Reviewers (2) -> Challengers (2) -> Forensic Auditor -> Gate.

### Phase 2: Integration & Hardening
- Milestone 4: 100% E2E test execution & bug fixes.
- Milestone 5: Tier 5 White-box adversarial coverage hardening.

### Phase 3: Final Reporting
- Validate final test results and forensic audit.
- Write handoff.md and send completion report to Sentinel.
