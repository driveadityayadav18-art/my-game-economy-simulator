# Original User Request

## 2026-09-27T08:23:06Z

Build Phase 1 of the AI-Driven Game Economy Simulator: an asynchronous FastAPI simulation engine where 3 autonomous persona agents (Garrick the Greedy, Cora the Farmer, Boran the Adventurer) trade items (Health Potion, Iron Sword, Raw Gem) under mathematical supply/demand price discovery, featuring multi-provider LLM support with heuristic fallback, policy REST controls, and automated verification suites.

Working directory: c:\Users\Aditya S Yadav\Desktop\anything-to-website\my-game-economy-simulator
Integrity mode: development

Reference specifications:
- `specs/constitution/project_mission.md`
- `specs/constitution/project_roadmap.md`
- `specs/constitution/tech_stack_specification.md`
- `specs/features/feature_specification_mvp_engine_dashboard (1).md`
- `src/system_execution_guide (1).md`

## Requirements

### R1. Deterministic Market & State Store (`src/`)
Implement an in-memory economic state store and mathematical price discovery engine.
- Calculate price adjustments based on net demand (\Delta D = Q_{\text{bought}} - Q_{\text{sold}}) using P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + k \cdot \Delta D)) with default sensitivity k = 0.05 and minimum price floor of 1.0 Gold.
- Support transactions for the 3 items: "Health Potion", "Iron Sword", "Raw Gem".
- Calculate transaction taxes T = P_{\text{unit}} \cdot r_{\text{tax}} and validate agent gold/inventory constraints before finalizing transactions.

### R2. Parallel Multi-Provider LLM Agent Module with Fallback
Implement agent decision modules for the 3 defined personas:
- **Garrick the Greedy:** Hoards rare items and gold; buys low, sells high aggressively.
- **Cora the Farmer:** Prioritizes steady income; sells raw materials consistently, avoids debt/risk.
- **Boran the Adventurer:** Prioritizes immediate consumption; spends gold on potions/weapons, maintains low balance.
- Support configurable LLM providers (OpenAI, Anthropic, or Gemini via `.env`) with structured JSON schema enforcement (`action`, `item`, `quantity`, `reasoning`).
- Execute all agent reasoning steps concurrently via `asyncio.gather()`.
- Provide an automatic simulated heuristic fallback mode when API keys are absent, network calls fail, or execution times out (>2.0s), ensuring the agent safely falls back to a valid action (e.g. "HOLD") without crashing.

### R3. Simulation Tick Loop & Policy REST API
Implement an asynchronous tick loop (~4 second interval) with FastAPI REST endpoints:
- `GET /state`: Returns complete economy snapshot (tick number, item prices, agent gold & inventories, current tax rate, recent transaction history).
- `POST /simulation/tick`: Triggers a single manual simulation tick for deterministic stepping.
- `POST /simulation/start` & `POST /simulation/stop`: Controls background tick loop execution.
- `POST /policy/tax`: Updates the tax rate r_{\text{tax}} (clamped between 0% and 80%).
- `POST /policy/event`: Triggers economic shock events ("Dragon Attack": Health Potion supply = 2, base price = 35.0 Gold; "Gold Rush": +100 Gold credited to all agents).

### R4. Automated Pytest Verification Suite
Implement a comprehensive pytest suite and test verification runner covering:
- Deterministic price calculation and floor boundary enforcement.
- Tax calculation accuracy.
- Policy events execution ("Dragon Attack", "Gold Rush").
- Agent JSON schema parsing and fallback execution when LLM outputs invalid data or times out.
- Tick concurrency execution timing under 2.0s.

## Acceptance Criteria

### Engine Integrity & Pricing Math
- [ ] Item prices update deterministically following P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + k \cdot \Delta D)) and never drop below 1.0 Gold.
- [ ] Tax deductions are correctly applied to transactions according to the current tax rate.
- [ ] Insufficient gold or inventory prevents invalid trades without corrupting state.

### Multi-Provider & Simulated Fallback
- [ ] Engine runs out-of-the-box in simulated fallback mode without requiring any API keys.
- [ ] Configured API keys (OpenAI / Anthropic / Gemini) correctly route prompt queries when provided.
- [ ] Invalid LLM outputs or delays over 2.0 seconds fall back safely to "HOLD" and log the fallback reason.

### Policy Controls & Events
- [ ] "Dragon Attack" shock sets Health Potion supply to 2 and base price to 35.0 Gold.
- [ ] "Gold Rush" shock immediately increments each agent's gold balance by +100.
- [ ] Tax updates via `POST /policy/tax` immediately affect subsequent tick transactions.

### Automated Testing & Timing
- [ ] All automated tests in `tests/` pass cleanly with `pytest`.
- [ ] Parallel agent tick evaluation completes within 2.0 seconds.
