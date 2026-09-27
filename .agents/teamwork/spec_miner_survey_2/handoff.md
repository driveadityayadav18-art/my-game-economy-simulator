# Specification Mining Report: Agent Personas, Multi-Provider LLM Framework, Tick Loop & REST API

**Agent**: `teamwork_preview_spec_miner_survey_2`  
**Working Directory**: `c:\Users\Aditya S Yadav\Desktop\anything-to-website\my-game-economy-simulator\.agents\teamwork\spec_miner_survey_2`  
**Date**: 2026-09-27  

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Agent Persona | Garrick the Greedy | Hoards rare items and gold; buys low, sells high aggressively; resents transaction taxes. | Current economy state, market prices, own inventory & gold. | `AgentDecision` (BUY/SELL/HOLD, item, quantity, reasoning). | If low on gold or inventory, trade fails validation; if LLM errors, fallback to HOLD. | `ORIGINAL_REQUEST.md:27`, `feature_specification_mvp_engine_dashboard (1).md:32-33` |
| 2 | Agent Persona | Cora the Farmer | Prioritizes steady income; sells raw materials consistently; avoids debt and speculative risk. | Current economy state, market prices, own inventory & gold. | `AgentDecision` (BUY/SELL/HOLD, item, quantity, reasoning). | Refuses risky trades; logs complaints/HOLD when tax $\ge 50\%$; fallback to HOLD on error. | `ORIGINAL_REQUEST.md:28`, `feature_specification_mvp_engine_dashboard (1).md:34-35`, `VAL-02` |
| 3 | Agent Persona | Boran the Adventurer | Prioritizes immediate consumption; spends gold on potions and weapons; maintains low gold balance. | Current economy state, market prices, own inventory & gold. | `AgentDecision` (BUY/SELL/HOLD, item, quantity, reasoning). | Insufficient gold blocks potion purchase; fallback to HOLD on LLM timeout/failure. | `ORIGINAL_REQUEST.md:29`, `feature_specification_mvp_engine_dashboard (1).md:36-37` |
| 4 | LLM Framework | Multi-Provider Engine | Configurable LLM adapter supporting OpenAI (`gpt-4o-mini`), Anthropic (`claude-3-5-haiku`), and Gemini via `.env`. | `.env` credentials (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`), agent prompt. | Raw LLM JSON string. | Unset key triggers fallback mode; provider API error triggers fallback to HOLD. | `ORIGINAL_REQUEST.md:30`, `tech_stack_specification.md:11`, `system_execution_guide (1).md:5,22` |
| 5 | LLM Framework | Structured JSON Schema Enforcement | Enforces strict JSON output schema: `action` (BUY, SELL, HOLD), `item` (Health Potion, Iron Sword, Raw Gem, null), `quantity` (1-10), `reasoning` (max 120 chars). | LLM generation payload. | Validated `AgentDecision` object. | Schema violation triggers Simulated Heuristic Fallback ("HOLD") with logged reason. | `feature_specification_mvp_engine_dashboard (1).md:39-52`, `ORIGINAL_REQUEST.md:30,47` |
| 6 | LLM Framework | Parallel Concurrency | Agent decisions are executed simultaneously via `asyncio.gather()` within a tick. | List of 3 async agent decision coroutines. | Tuple of 3 `AgentDecision` objects. | Exceptions in individual tasks handled safely without terminating other agents. | `ORIGINAL_REQUEST.md:31,48,69`, `tech_stack_specification.md:16` |
| 7 | LLM Framework | Simulated Heuristic Fallback | Automatic fallback returning a valid "HOLD" decision without external API calls or crashes. | Trigger event: missing API key, network error, or timeout >2.0s. | Valid `AgentDecision(action="HOLD", item=None, quantity=1, reasoning="Fallback: ...")`. | Guaranteed valid output; logs exact fallback reason; zero uncaught exceptions. | `ORIGINAL_REQUEST.md:32,58,60`, `tech_stack_specification.md:17`, `VAL-04` |
| 8 | Simulation Loop | Asynchronous Tick Loop | Background loop executing simulation ticks every ~4.0 seconds. | Start command, interval (4s). | Periodic tick execution, state mutation, and WebSocket broadcast. | Sleep adjustment for execution time; graceful cancellation on stop. | `ORIGINAL_REQUEST.md:35`, `feature_specification_mvp_engine_dashboard (1).md:6`, `VAL-01` |
| 9 | Simulation Loop | Manual Tick Stepping | Synchronous single-tick trigger for deterministic step-by-step evaluation and testing. | `POST /simulation/tick` request. | Updated state snapshot after 1 tick. | Rejects reentrant tick calls while tick is currently in progress. | `ORIGINAL_REQUEST.md:37` |
| 10 | REST API | `GET /state` | Returns complete economic snapshot: tick number, item prices & supplies, agent gold & inventories, tax rate, recent transactions. | None. | JSON containing full economy state. | Returns current snapshot; thread/async safe read. | `ORIGINAL_REQUEST.md:36` |
| 11 | REST API | `POST /simulation/tick` | Executes exactly one simulation tick deterministically. | Empty body `{}`. | JSON containing updated state snapshot and tick metrics. | Returns error if tick execution fails. | `ORIGINAL_REQUEST.md:37` |
| 12 | REST API | `POST /simulation/start` | Initiates the background 4-second tick loop. | Empty body `{}`. | Status confirmation: `{ "success": true, "running": true }`. | If already running, returns status without spawning duplicate loop. | `ORIGINAL_REQUEST.md:38` |
| 13 | REST API | `POST /simulation/stop` | Terminates the running background tick loop. | Empty body `{}`. | Status confirmation: `{ "success": true, "running": false }`. | If already stopped, idempotent success response. | `ORIGINAL_REQUEST.md:38` |
| 14 | REST API | `POST /policy/tax` | Updates central bank transaction tax rate $r_{\text{tax}}$, clamped between 0% and 80% ($0.0 - 0.80$). | Body: `{ "tax_rate": float }`. | Updated tax rate confirmation. | Rejects or clamps values outside $[0.0, 0.80]$; returns 422 if invalid type. | `ORIGINAL_REQUEST.md:39,65`, `feature_specification_mvp_engine_dashboard (1).md:55` |
| 15 | REST API | `POST /policy/event` | Injects economic shock events ("Dragon Attack", "Gold Rush"). | Body: `{ "event": string }`. | Event acknowledgment & state impact details. | Unknown event name returns 400 Bad Request. | `ORIGINAL_REQUEST.md:40,63-64`, `feature_specification_mvp_engine_dashboard (1).md:56-57` |
| 16 | Policy Shocks | Dragon Attack Event | Economic shock setting Health Potion market supply to 2 and base price to 35.0 Gold. | Policy trigger `"Dragon Attack"`. | Mutated market state (`Health Potion.price = 35.0`, `supply = 2`). | Idempotent state override; triggers price spike alerts. | `ORIGINAL_REQUEST.md:40,63`, `feature_specification_mvp_engine_dashboard (1).md:56`, `VAL-03` |
| 17 | Policy Shocks | Gold Rush Event | Economic shock immediately crediting $+100$ Gold to every agent's balance. | Policy trigger `"Gold Rush"`. | Mutated agent states ($\text{gold}_i \leftarrow \text{gold}_i + 100$). | All active agents credited simultaneously. | `ORIGINAL_REQUEST.md:40,64`, `feature_specification_mvp_engine_dashboard (1).md:57` |
| 18 | Real-time Streaming | WebSocket Broadcast | Real-time state broadcasting endpoint (`/ws`) for live dashboard updates every tick. | Client WebSocket connection. | Streamed JSON state payload on tick completion. | Disconnected clients cleanly removed without interrupting tick loop. | `tech_stack_specification.md:10`, `feature_specification_mvp_engine_dashboard (1).md:9`, `VAL-05` |

---

## Edge Cases

| # | Feature | Input | Observed / Expected Behavior |
|---|---------|-------|-------------------------------|
| 1 | Agent Decision Validation | Agent selects BUY but has insufficient Gold: $\text{gold} < P_{\text{unit}} \cdot Q \cdot (1 + r_{\text{tax}})$. | Transaction rejected; agent gold and market state remain unchanged; logged as failed validation. |
| 2 | Agent Decision Validation | Agent selects SELL but owns fewer items than $Q$: $\text{inventory}[item] < Q$. | Transaction rejected; agent inventory remains unchanged; state integrity preserved. |
| 3 | LLM JSON Schema | LLM returns action `"HOLD"` with `"item": null` and `"quantity": 0` when schema requires `"minimum": 1`. | Schema validation fails if minimum 1 is strictly applied; schema or parser must allow quantity 0 or ignore quantity on HOLD, or agent must output quantity 1 for HOLD. |
| 4 | LLM JSON Schema | LLM outputs `action: "CRAFT"` (allowed in spec schema line 45, but no recipe in Phase 1). | System treats CRAFT as unsupported in Phase 1, safely converting to `"HOLD"` or no-op transaction without crash. |
| 5 | LLM JSON Schema | LLM returns reasoning string exceeding 120 characters ($>120$ chars). | Violates `maxLength: 120`. Parser should truncate string to 120 characters or fallback to HOLD. |
| 6 | Concurrency / Timing | LLM network call hangs or takes 2.5s (exceeding 2.0s execution window). | `asyncio.wait_for(timeout=2.0)` cancels the task, raises `TimeoutError`, and triggers fallback to HOLD with `reasoning="Fallback: LLM request timed out > 2.0s"`. |
| 7 | Multi-Provider Config | No API keys set in `.env` (fresh repo clone). | Engine detects missing keys on initialization, operates entirely in Simulated Heuristic Fallback mode out-of-the-box without crashing. |
| 8 | Multi-Provider Config | Malformed JSON returned from LLM (e.g. Markdown code fences or invalid syntax). | JSON parser catches error, logs raw response, safely returns fallback `"HOLD"` decision. |
| 9 | Policy Tax Clamping | User sends `POST /policy/tax` with `{"tax_rate": 0.95}` or `{"tax_rate": -0.10}`. | System clamps value to $[0.0, 0.80]$ ($95\% \to 80\%$, $-10\% \to 0\%$) or rejects with HTTP 422 Unprocessable Entity. |
| 10 | Background Loop Control | Calling `POST /simulation/start` when loop is already running. | Engine recognizes active task, returns `{ "running": true, "message": "Already running" }` without launching duplicate background tasks. |
| 11 | Deterministic Pricing Floor | Aggressive selling drives price below 1.0 Gold ($P_{\text{old}} \cdot (1 + k \cdot \Delta D) < 1.0$). | Price is capped by $\max(1.0, \dots)$, strictly enforcing the 1.0 Gold floor boundary. |
| 12 | Agent Wealth Invariant | Heavy taxes applied to transaction ($r_{\text{tax}} = 0.80$). | Tax calculation $T = P_{\text{unit}} \cdot r_{\text{tax}}$ applies accurately; agent gold never goes negative. |

---

## 5-Component Handoff Report

### 1. Observation

Directly observed facts and citations from repository files:

1. **`ORIGINAL_REQUEST.md`**:
   - Lines 5: "Build Phase 1 of the AI-Driven Game Economy Simulator: an asynchronous FastAPI simulation engine where 3 autonomous persona agents (Garrick the Greedy, Cora the Farmer, Boran the Adventurer) trade items (Health Potion, Iron Sword, Raw Gem) under mathematical supply/demand price discovery, featuring multi-provider LLM support with heuristic fallback, policy REST controls, and automated verification suites."
   - Lines 25-33 (R2):
     - Personas: "Garrick the Greedy: Hoards rare items and gold; buys low, sells high aggressively."
     - "Cora the Farmer: Prioritizes steady income; sells raw materials consistently, avoids debt/risk."
     - "Boran the Adventurer: Prioritizes immediate consumption; spends gold on potions/weapons, maintains low balance."
     - "Support configurable LLM providers (OpenAI, Anthropic, or Gemini via `.env`) with structured JSON schema enforcement (`action`, `item`, `quantity`, `reasoning`)."
     - "Execute all agent reasoning steps concurrently via `asyncio.gather()`."
     - "Provide an automatic simulated heuristic fallback mode when API keys are absent, network calls fail, or execution times out (>2.0s), ensuring the agent safely falls back to a valid action (e.g. 'HOLD') without crashing."
   - Lines 35-41 (R3):
     - "Simulation tick loop (~4 second interval) with FastAPI REST endpoints:
       - `GET /state`: Returns complete economy snapshot (tick number, item prices, agent gold & inventories, current tax rate, recent transaction history).
       - `POST /simulation/tick`: Triggers a single manual simulation tick for deterministic stepping.
       - `POST /simulation/start` & `POST /simulation/stop`: Controls background tick loop execution.
       - `POST /policy/tax`: Updates the tax rate $r_{\text{tax}}$ (clamped between 0% and 80%).
       - `POST /policy/event`: Triggers economic shock events ('Dragon Attack': Health Potion supply = 2, base price = 35.0 Gold; 'Gold Rush': +100 Gold credited to all agents)."
   - Lines 58-60 & 68-69 (Acceptance Criteria):
     - "Engine runs out-of-the-box in simulated fallback mode without requiring any API keys."
     - "Invalid LLM outputs or delays over 2.0 seconds fall back safely to 'HOLD' and log the fallback reason."
     - "Parallel agent tick evaluation completes within 2.0 seconds."

2. **`specs/features/feature_specification_mvp_engine_dashboard (1).md`**:
   - Lines 40-52: Agent Decision JSON Schema:
     ```json
     {
       "$schema": "http://json-schema.org/draft-07/schema#",
       "type": "object",
       "properties": {
         "action": { "type": "string", "enum": ["BUY", "SELL", "CRAFT", "HOLD"] },
         "item": { "type": ["string", "null"], "enum": ["Health Potion", "Iron Sword", "Raw Gem", null] },
         "quantity": { "type": "integer", "minimum": 1, "maximum": 10 },
         "reasoning": { "type": "string", "maxLength": 120 }
       },
       "required": ["action", "item", "quantity", "reasoning"]
     }
     ```
   - Lines 63-69: Validation Scorecard:
     - VAL-01: "Loop executes every 4s, querying 3 agents in parallel. Engine completes tick in $<2.0$ seconds."
     - VAL-02: "GM increases tax to 50%. Agents log 'HOLD' or complaints about high taxes in reasoning."
     - VAL-03: "Dragon Attack Shock: Event triggered via UI. Potion price spikes above 25.0 Gold; News headline triggers alert."
     - VAL-04: "Invalid LLM Response: LLM returns non-JSON text. System falls back gracefully to 'HOLD' without crashing loop."

3. **`specs/constitution/tech_stack_specification.md`**:
   - Line 9: "Backend API Engine: Python 3.11+, FastAPI, Uvicorn (High performance asynchronous execution required for parallel LLM API calls and WebSocket streaming)."
   - Line 11: "LLM Integration: OpenAI API (`gpt-4o-mini`) or Anthropic API (`claude-3-5-haiku`)."
   - Line 12: "State Storage: In-Memory Data Structures (Python Dicts)."
   - Line 16: "Parallel Execution: Agent reasoning steps per tick MUST execute asynchronously via `asyncio.gather()` to keep tick latency under 2 seconds."
   - Line 17: "Fail-Safe Fallbacks: If an LLM call fails or times out (over 2.5 seconds), the agent must default to a 'HOLD' action with a logged reason."

4. **`src/system_execution_guide (1).md`**:
   - Line 17: `pip install fastapi uvicorn openai websockets`
   - Line 27: `uvicorn main:app --reload --port 8000`

---

### 2. Logic Chain

From the observations, we deduce the following structural and behavioral requirements:

1. **Persona Design & Initial Balances**:
   - The specifications define 3 personas: Garrick (greedy hoarder), Cora (prudent farmer), Boran (impulsive adventurer).
   - Although specific initial numerical inventories/gold balances are not locked down in a hardcoded constant table in `feature_specification_mvp_engine_dashboard (1).md`, the economy requires initial balances for all 3 items ("Health Potion", "Iron Sword", "Raw Gem") and gold so trades can occur on tick 1:
     - **Garrick the Greedy**: High gold reserve and valuable assets. Initial: Gold = 150.0, Inventory = `{"Health Potion": 2, "Iron Sword": 1, "Raw Gem": 5}`.
     - **Cora the Farmer**: High raw goods, moderate gold, no luxury items. Initial: Gold = 60.0, Inventory = `{"Health Potion": 2, "Iron Sword": 0, "Raw Gem": 10}`.
     - **Boran the Adventurer**: Low gold, spends on weapons/potions immediately. Initial: Gold = 40.0, Inventory = `{"Health Potion": 1, "Iron Sword": 1, "Raw Gem": 0}`.
   - Persona prompt templates must feed current market prices, own inventory, gold, and current tax rate to the LLM with clear persona goals.
   - For tax sensitivity (VAL-02), prompt instructions must instruct agents to evaluate tax impact: if tax rate is excessive ($\ge 50\%$), Cora and Garrick should favor HOLD or complain in their reasoning.

2. **Multi-Provider LLM Agent Architecture**:
   - Supported providers: OpenAI (`gpt-4o-mini`), Anthropic (`claude-3-5-haiku`), Gemini (`gemini-1.5-flash` or `gemini-2.0-flash`).
   - Provider selection:
     1. Check `.env` variable `LLM_PROVIDER` (or detect presence of `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`).
     2. If no valid key is provided, or `MOCK_LLM=true` / `SIMULATED_MODE=true`, automatically switch to **Simulated Heuristic Fallback mode**.
   - Structured JSON schema enforcement:
     - Use Pydantic schema matching the draft-07 JSON schema.
     - Fields: `action: Literal["BUY", "SELL", "HOLD"]` (or optional `"CRAFT"`), `item: Optional[Literal["Health Potion", "Iron Sword", "Raw Gem"]] = None`, `quantity: int = Field(ge=1, le=10)`, `reasoning: str = Field(max_length=120)`.
     - In simulated fallback or when `action == "HOLD"`, `item` is `None`, `quantity` is `1` (to satisfy `minimum: 1`), and `reasoning` contains the fallback justification.

3. **Concurrency and Timeout Constraints**:
   - `ORIGINAL_REQUEST.md` specifies $>2.0$s timeout for fallback, while `tech_stack_specification.md` mentions $2.5$s, and VAL-01 requires completing tick in $<2.0$s.
   - **Resolution**: Strict adherence to the $2.0$ second window is required. Individual agent LLM calls must be wrapped in `asyncio.wait_for(..., timeout=2.0)`.
   - All 3 agents are queried in parallel using `asyncio.gather(*[agent.decide(...) for agent in agents])`.
   - Wrapping with `asyncio.gather(..., return_exceptions=True)` or handling exceptions inside `agent.decide(...)` ensures a timeout or failure in one agent does not cancel or crash the decisions of the other agents.

4. **Simulated Heuristic Fallback Strategy**:
   - Fallback is triggered upon:
     a) Missing API keys on initialization or runtime.
     b) Provider network exceptions, HTTP errors, 429 rate limits, 500 server errors.
     c) Timeout exceeding $2.0$s.
     d) Pydantic / JSON schema validation failure.
   - When triggered, return:
     `AgentDecision(action="HOLD", item=None, quantity=1, reasoning=f"Fallback: {reason[:100]}")`.
   - For offline simulation without API keys, heuristic behavior can also simulate deterministic persona actions (e.g. Cora selling 1 Raw Gem if she has gems, Boran buying 1 potion if he has gold, Garrick buying if price < base), while falling back safely to HOLD on errors.

5. **Tick Loop & REST API Architecture**:
   - Single in-memory state store containing:
     - `tick`: integer (starts at 0).
     - `running`: boolean.
     - `tax_rate`: float (default e.g. 0.05, clamped between 0.0 and 0.80).
     - `items`: dict mapping item name to `{"price": float, "supply": int}`.
     - `agents`: dict mapping agent name to `{"gold": float, "inventory": dict, "last_action": dict}`.
     - `recent_transactions`: list of past transactions (capped at e.g. 50 entries).
   - **Manual vs Background execution**:
     - `POST /simulation/tick`: executes one tick synchronously, updates state, and returns state.
     - `POST /simulation/start`: creates an `asyncio.create_task(run_tick_loop())` running while `running == True`.
     - `POST /simulation/stop`: sets `running = False` and cancels background task.
   - **Policy controls**:
     - `POST /policy/tax`: updates `tax_rate`, clamping to $[0.0, 0.80]$.
     - `POST /policy/event`:
       - `"Dragon Attack"`: sets `items["Health Potion"]["supply"] = 2`, `items["Health Potion"]["price"] = 35.0`.
       - `"Gold Rush"`: adds `100.0` gold to all agents in `agents`.

---

### 3. Caveats

1. **Timeout discrepancy**: `tech_stack_specification.md` line 17 states "over 2.5 seconds", but `ORIGINAL_REQUEST.md` lines 32, 48, 60, 69 and `VAL-01` state "$<2.0$ seconds" / "$>2.0$s". The stricter $2.0$s constraint MUST take precedence for implementation and test assertions.
2. **"CRAFT" action ambiguity**: `feature_specification_mvp_engine_dashboard (1).md` line 45 lists `"CRAFT"` in the action enum, but neither recipes nor crafting mechanics are defined in Phase 1 specs. `ORIGINAL_REQUEST.md` line 30 specifies `action (BUY, SELL, HOLD)`. If `"CRAFT"` is received, the engine should treat it as unsupported in Phase 1 and default to HOLD or no-op.
3. **Quantity constraint on HOLD**: The draft-07 schema specifies `"quantity": { "type": "integer", "minimum": 1, "maximum": 10 }`. If an agent is holding, setting quantity to 0 would fail strict draft-07 validation if `minimum: 1` is enforced. Therefore, either quantity should default to `1` on HOLD, or the schema validation should permit `0` when action is `"HOLD"`.
4. **WebSocket vs REST scope**: Tech stack and feature spec define `/ws` for streaming, while Phase 1 MVP requirements in `ORIGINAL_REQUEST.md` prioritize the REST endpoints (`GET /state`, `POST /simulation/tick`, etc.). Providing both `/ws` and REST ensures full compatibility with both Phase 1 and Phase 2 dashboard readiness.

---

### 4. Conclusion

Phase 1 specification mining for Agent Personas, Multi-Provider LLM Agent Framework, Tick Loop & REST API provides an unambiguous blueprint:
1. **Three Autonomous Personas**: Garrick the Greedy, Cora the Farmer, and Boran the Adventurer, each with distinct starting balances, psychological motivations, and tax sensitivities.
2. **Multi-Provider Resilience**: Configurable for OpenAI, Anthropic, and Gemini via `.env`, with out-of-the-box zero-dependency Simulated Heuristic Fallback mode that defaults safely to `"HOLD"` with logged reason whenever API keys are absent, timeouts exceed 2.0s, or outputs are invalid.
3. **Structured Strict Schema**: Pydantic / Draft-07 JSON schema enforcing action (`BUY`, `SELL`, `HOLD`), item (`Health Potion`, `Iron Sword`, `Raw Gem`, or `null`), quantity ($1-10$), and reasoning ($\le 120$ chars).
4. **Deterministic Loop & REST API**: Manual stepping via `POST /simulation/tick`, background loop via `POST /simulation/start` and `POST /simulation/stop`, state inspection via `GET /state`, tax regulation via `POST /policy/tax` ($0\%-80\%$), and economic shocks via `POST /policy/event` ("Dragon Attack" and "Gold Rush").
5. **Concurrency Ceiling**: Sub-2.0 second parallel execution via `asyncio.gather()`.

---

### 5. Verification Method

To independently verify these findings against the authoritative specification files:
1. **Inspect Personas**:
   - `specs/features/feature_specification_mvp_engine_dashboard (1).md`: lines 32–37
   - `ORIGINAL_REQUEST.md`: lines 27–29
2. **Inspect Decision JSON Schema**:
   - `specs/features/feature_specification_mvp_engine_dashboard (1).md`: lines 40–52
3. **Inspect REST Endpoints & Shock Events**:
   - `ORIGINAL_REQUEST.md`: lines 35–41
   - `specs/features/feature_specification_mvp_engine_dashboard (1).md`: lines 54–58
4. **Inspect Concurrency & Timeout Requirements**:
   - `ORIGINAL_REQUEST.md`: lines 31–32, 48, 60, 69
   - `specs/constitution/tech_stack_specification.md`: lines 14–18
   - `specs/features/feature_specification_mvp_engine_dashboard (1).md`: lines 63–69 (`VAL-01` to `VAL-05`)
