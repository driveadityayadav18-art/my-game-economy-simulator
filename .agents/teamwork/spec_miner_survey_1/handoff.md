# Specification Mining Report: Core Market Math, Policy Shocks & Invariants

## Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Market Pricing | Net Demand Calculation | Computes net tick demand $\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$ aggregated across all validated agent transactions in a tick. | List of transactions in tick: $Q_{\text{bought}}$ (total units bought), $Q_{\text{sold}}$ (total units sold) per item. | Scalar $\Delta D \in \mathbb{Z}$ per item. | Zero transactions yield $\Delta D = 0$. Invalid/rejected transactions must not contribute to $Q_{\text{bought}}$ or $Q_{\text{sold}}$. | `feature_specification_mvp_engine_dashboard (1).md:13-20`, `ORIGINAL_REQUEST.md:21` |
| 2 | Market Pricing | Algorithmic Price Discovery | Adjusts item price deterministically using $P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + k \cdot \Delta D))$. | $P_{\text{old}}$ (current item price, float $\ge 1.0$), $k$ (sensitivity coefficient, default $0.05$), $\Delta D$ (net demand). | $P_{\text{new}}$ (updated item price, float $\ge 1.0$). | If calculated price $< 1.0$, floor function caps price at minimum $1.0$ Gold. | `feature_specification_mvp_engine_dashboard (1).md:15-21`, `ORIGINAL_REQUEST.md:21, 53` |
| 3 | Market Pricing | Minimum Price Floor Enforcement | Hard boundary invariant ensuring no item price falls below 1.0 Gold regardless of massive negative demand or sell shocks. | Item price calculation result $P_{\text{calc}}$. | $\max(1.0, P_{\text{calc}})$. | Price never goes negative or zero; minimum return value is strictly $1.0$. | `feature_specification_mvp_engine_dashboard (1).md:21`, `ORIGINAL_REQUEST.md:21, 53` |
| 4 | Item Economy | Supported Item Catalog | The simulation supports exactly 3 item types: "Health Potion", "Iron Sword", and "Raw Gem". | Item name string. | Validated item identifier enum `["Health Potion", "Iron Sword", "Raw Gem"]`. | Unknown item string fails schema validation; triggers agent fallback to "HOLD". | `feature_specification_mvp_engine_dashboard (1).md:17, 46`, `ORIGINAL_REQUEST.md:22` |
| 5 | Item Economy | Market Inventory Tracking | Tracks current available market supply for items. Normal baseline supply vs constrained supply (e.g. Dragon Attack supply = 2). | Item name, delta quantity. | Updated market inventory integer $\ge 0$. | Attempting to buy more units than available in market supply fails or caps to available inventory. | `feature_specification_mvp_engine_dashboard (1).md:56`, `ORIGINAL_REQUEST.md:40, 63` |
| 6 | Taxation | Transaction Tax Calculation | Calculates tax per unit $T = P_{\text{unit}} \cdot r_{\text{tax}}$, and total tax $T_{\text{total}} = Q \cdot P_{\text{unit}} \cdot r_{\text{tax}}$. | Unit price $P_{\text{unit}}$, transaction quantity $Q$, tax rate $r_{\text{tax}}$. | Tax amount $T \ge 0.0$ (Gold). | Tax cannot be negative. If $r_{\text{tax}} = 0$, $T = 0.0$. | `feature_specification_mvp_engine_dashboard (1).md:23-25`, `ORIGINAL_REQUEST.md:23` |
| 7 | Policy Control | Tax Rate Adjustment (`POST /policy/tax`) | Updates the macroeconomic transaction tax rate $r_{\text{tax}}$ clamped between $0\%$ and $80\%$ ($0.0 \le r_{\text{tax}} \le 0.80$). | JSON body `{"tax_rate": float}` or query param. | HTTP 200 with updated tax rate; immediately takes effect on subsequent tick transactions. | Rates outside $[0.0, 0.80]$ clamped or rejected with 400 Bad Request. | `feature_specification_mvp_engine_dashboard (1).md:55`, `ORIGINAL_REQUEST.md:39, 65` |
| 8 | Transaction Engine | Buyer Gold Validation | Validates that an agent purchasing items possesses sufficient gold balance to cover purchase price plus tax: $\text{gold} \ge Q \cdot P_{\text{unit}} + T_{\text{total}}$. | Agent ID, item, quantity $Q$, price $P$, tax rate $r_{\text{tax}}$. | Boolean validation status: True (proceed) or False (reject). | If $\text{gold} < \text{total\_cost}$, transaction rejected, 0 gold deducted, 0 items transferred, no price distortion. | `ORIGINAL_REQUEST.md:23, 55` |
| 9 | Transaction Engine | Seller Inventory Validation | Validates that an agent selling items holds sufficient inventory: $\text{agent.inventory}[item] \ge Q$. | Agent ID, item, quantity $Q$. | Boolean validation status: True (proceed) or False (reject). | If inventory insufficient, transaction rejected, 0 items deducted, 0 gold credited. | `ORIGINAL_REQUEST.md:23, 55` |
| 10 | Transaction Engine | Atomic State Finalization | Executes state mutation only after all balance and inventory checks pass; credits/debits agent and market accounts atomically. | Validated transaction order. | Mutated state store (agent balances, inventories, transaction log). | Any error causes immediate rollback or rejection without partial mutation. | `ORIGINAL_REQUEST.md:23, 55` |
| 11 | Policy Shocks | "Dragon Attack" Shock Event | Economic shock that instantly sets Health Potion market supply to $2$ and base price to $35.0$ Gold, causing immediate potion scarcity. | `POST /policy/event` with `{"event": "Dragon Attack"}` (or `{"event_type": "dragon_attack"}`). | Health Potion supply = 2, Health Potion price = 35.0 Gold, news event alert logged. | Unrecognized event string returns 400/422; Potion state intact. | `feature_specification_mvp_engine_dashboard (1).md:56, 67`, `ORIGINAL_REQUEST.md:40, 63` |
| 12 | Policy Shocks | "Gold Rush" Shock Event | Economic shock that instantly credits $+100$ Gold to every agent's balance in the simulation. | `POST /policy/event` with `{"event": "Gold Rush"}` (or `{"event_type": "gold_rush"}`). | For every agent $a$, $\text{gold}_a \mathrel{+}= 100.0$; event logged. | Unrecognized event returns 400/422. | `feature_specification_mvp_engine_dashboard (1).md:57`, `ORIGINAL_REQUEST.md:40, 64` |
| 13 | State Inspection | Full Economy Snapshot (`GET /state`) | Returns complete serialized state including tick number, item prices, agent gold & inventories, current tax rate, and recent transactions. | HTTP GET `/state`. | JSON object with `tick`, `items`, `agents`, `tax_rate`, `recent_transactions`. | Always returns 200 OK with valid JSON structure. | `ORIGINAL_REQUEST.md:36` |
| 14 | Simulation Control | Single Tick Stepping (`POST /simulation/tick`) | Executes exactly one deterministic simulation step: queries agents, validates actions, updates prices, logs results. | HTTP POST `/simulation/tick`. | JSON result containing tick summary, agent actions, executed transactions, new prices. | Any agent timeout falls back to HOLD; tick completes in $< 2.0\text{s}$. | `ORIGINAL_REQUEST.md:37, 48, 69`, `feature_specification_mvp_engine_dashboard (1).md:65` |
| 15 | Simulation Control | Loop Execution (`POST /simulation/start`, `/stop`) | Starts or stops the background async loop running simulation ticks every 4 seconds. | HTTP POST `/simulation/start`, `POST /simulation/stop`. | JSON status message `{"status": "running"|"stopped"}`. | Starting already-running or stopping stopped loop is idempotent. | `ORIGINAL_REQUEST.md:38`, `feature_specification_mvp_engine_dashboard (1).md:6` |
| 16 | Agent Module | Decision JSON Schema Enforcement | Validates agent output against strict schema: `action` (BUY, SELL, CRAFT, HOLD), `item` (Health Potion, Iron Sword, Raw Gem, or null), `quantity` (1-10), `reasoning` (max 120 chars). | Raw string or JSON from LLM or heuristic fallback. | Validated typed `AgentDecision` object. | Schema mismatch or JSON parsing failure triggers immediate safe fallback to `HOLD`. | `feature_specification_mvp_engine_dashboard (1).md:40-52, 68`, `tech_stack_specification.md:15` |
| 17 | Agent Module | Simulated Heuristic Fallback Mode | Provides out-of-the-box rule-based decisions per persona when API keys are absent, network fails, or latency exceeds 2.0s. | Current agent persona, market state. | Valid `AgentDecision` (e.g. HOLD or persona heuristic action) with logged fallback reason. | Guarantees engine never halts or throws unhandled exception on missing keys/timeouts. | `ORIGINAL_REQUEST.md:32, 58, 60`, `tech_stack_specification.md:17` |
| 18 | Real-Time Sync | WebSocket State Streaming (`/ws`) | Streams economy snapshot JSON to connected UI clients on every tick. | WebSocket connection request to `/ws`. | Continuous JSON state frames per tick. | Disconnected clients handled gracefully without interrupting simulation. | `tech_stack_specification.md:10`, `feature_specification_mvp_engine_dashboard (1).md:9, 69` |

---

## Edge Cases
| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Algorithmic Price Discovery | $\Delta D = 0$ (Equal buys and sells, e.g., 2 bought, 2 sold; or all agents HOLD) | $P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + 0.05 \cdot 0)) = P_{\text{old}}$. Price remains completely unchanged. |
| 2 | Algorithmic Price Discovery | Massive net sell-off ($\Delta D \le -20$, e.g., $\Delta D = -25$ when $P_{\text{old}} = 2.0$) | $P_{\text{calc}} = 2.0 \cdot (1 + 0.05 \cdot (-25)) = 2.0 \cdot (-0.25) = -0.50$. Hard floor $\max(1.0, -0.50)$ clamps price to $1.0$ Gold. Price never drops below $1.0$. |
| 3 | Algorithmic Price Discovery | Item price already at floor $P_{\text{old}} = 1.0$ and additional sell occurs ($\Delta D = -5$) | $P_{\text{calc}} = 1.0 \cdot (1 - 0.25) = 0.75 \implies P_{\text{new}} = \max(1.0, 0.75) = 1.0$. Remains pinned at $1.0$ Gold. |
| 4 | Tax Calculation | Zero tax rate ($r_{\text{tax}} = 0.0$) | $T = P_{\text{unit}} \cdot 0.0 = 0.0$. Total cost equals base price; no tax collected. |
| 5 | Tax Calculation | Maximum tax rate ($r_{\text{tax}} = 0.80$) | $T = P_{\text{unit}} \cdot 0.80$. Total purchase cost per unit is $1.80 \cdot P_{\text{unit}}$. |
| 6 | Policy Tax API | Tax rate input out of bounds ($r_{\text{tax}} < 0.0$ or $r_{\text{tax}} > 0.80$, e.g., $1.5$ or $-0.1$) | Input must be rejected with HTTP 400/422 Unprocessable Entity or clamped strictly to $[0.0, 0.80]$. |
| 7 | Transaction Validation | Agent Gold exactly equals total cost ($\text{gold} = Q \cdot P_{\text{unit}} + T$) | Transaction validates successfully. Agent's gold balance becomes exactly $0.0$. |
| 8 | Transaction Validation | Agent Gold insufficient by fractional amount ($\text{gold} = 15.0$, cost = $15.01$) | Transaction fails validation. State remains unchanged: 0 gold deducted, 0 items received, transaction marked rejected/skipped in logs. |
| 9 | Transaction Validation | Agent attempts SELL with quantity $> \text{agent.inventory}[item]$ (e.g. owns 0, tries to sell 1) | Transaction fails validation. Inventory cannot become negative; 0 gold credited to agent. |
| 10 | Transaction Validation | Agent action `"HOLD"` with `item = null` and `quantity = 1` | Valid per schema (`item: ["string", "null"]`). No state changes, no gold or inventory mutation, $\Delta D = 0$. |
| 11 | Transaction Validation | Agent action `"BUY"` with `item = null` | Schema/engine validation error: buying requires an item name. Falls back to "HOLD" or rejected. |
| 12 | Agent Schema Validation | Quantity outside $[1, 10]$ (e.g. $0$, $-1$, or $15$) | Schema validation fails (`minimum: 1, maximum: 10`). Action rejected; agent falls back to `"HOLD"`. |
| 13 | Policy Shocks | "Dragon Attack" triggered when Health Potion market supply $< 2$ (e.g. 0) or $> 2$ (e.g. 10) | Supply is deterministically overwritten to exactly $2$ and price overwritten to $35.0$ Gold. |
| 14 | Policy Shocks | "Dragon Attack" when Health Potion price is already $> 35.0$ Gold | Base price is set to $35.0$ Gold per shock spec (resetting base price), while triggering the alert headline. |
| 15 | Policy Shocks | Market Supply Exhaustion (Agent orders $Q = 5$ Health Potions, but market supply is only $2$) | Trade cannot be filled in full. Must reject order or partial-fill to available supply without driving market inventory negative. |
| 16 | LLM Fallback | Execution latency exceeds $2.0$ seconds | Asynchronous timeout cancels/abandons LLM call; agent defaults to `"HOLD"` with logged reason `"timeout: latency exceeded 2.0s"`. |
| 17 | LLM Fallback | No API keys configured in environment (`.env`) | Engine boots out-of-the-box in simulated heuristic fallback mode; all agents execute persona-based fallback actions cleanly without crashing. |
| 18 | Precision / Rounding | Floating point multiplication drift (e.g. $10.0 \cdot 1.05 = 10.500000000000002$) | Prices and gold balances should be maintained/displayed rounded to 2 decimal places to maintain clean JSON and UI rendering. |

---

## 5-Component Handoff Report

### 1. Observation
Authoritative sources examined:
1. `specs/constitution/project_mission.md` (lines 15-22):
   > "In Scope for MVP:
   > - 3 AI agents with distinct personas and emotional states.
   > - 3 economy items ("Health Potion", "Iron Sword", "Raw Gem").
   > - Automated simulation tick loop (3–5 seconds per turn).
   > - Dynamic supply/demand pricing engine.
   > - Policy controls (Tax Rate slider, Trigger Events like 'Dragon Attack' or 'Gold Rush').
   > - Anomaly detection (Spike/Crash detection with AI news alerts).
   > - Live dashboard with price graphs, activity log, and agent balances."
2. `specs/constitution/project_roadmap.md` (lines 3-9):
   > "Phase 1: MVP Core Simulation Engine (Milestone 1)
   > - Implement FastAPI backend with in-memory economic state store.
   > - Construct LLM agent prompt templates with structured JSON output enforcement.
   > - Develop deterministic supply/demand price discovery engine.
   > - Implement async execution tick loop (4-second interval)."
3. `specs/constitution/tech_stack_specification.md` (lines 14-18):
   > "Architectural Constraints & Non-Negotiables:
   > - Strict JSON Parsing: All agent LLM calls must enforce JSON schema outputs to prevent simulation crashes due to malformed text.
   > - Parallel Execution: Agent reasoning steps per tick MUST execute asynchronously via `asyncio.gather()` to keep tick latency under 2 seconds.
   > - Fail-Safe Fallbacks: If an LLM call fails or times out (over 2.5 seconds), the agent must default to a 'HOLD' action with a logged reason.
   > - Decoupled Pricing Engine: The market price formula must be mathematical and deterministic, influenced by agent transaction volumes rather than arbitrary LLM decisions."
4. `specs/features/feature_specification_mvp_engine_dashboard (1).md` (lines 12-26, 39-58, 63-69):
   > "Price adjustments are calculated based on net demand ($\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$) using the following formula:
   > $P_{\text{new}} = \max\left(1.0, P_{\text{old}} \cdot \left(1 + k \cdot \Delta D\right)\right)$
   > Where:
   > $P_{\text{old}}$ = Current price of item
   > $k$ = Sensitivity coefficient (default: $0.05$)
   > $\Delta D$ = Net transaction quantity in current tick
   > Minimum price bound = $1.0$ Gold
   > Tax deduction formula for transactions:
   > $T = P_{\text{unit}} \cdot r_{\text{tax}}$"
   >
   > "Agent Decision JSON Schema:
   > action: enum ['BUY', 'SELL', 'CRAFT', 'HOLD']
   > item: enum ['Health Potion', 'Iron Sword', 'Raw Gem', null]
   > quantity: integer, minimum: 1, maximum: 10
   > reasoning: string, maxLength: 120
   > required: ['action', 'item', 'quantity', 'reasoning']"
   >
   > "GM Controls:
   > - Tax Rate Control: Slider ranging from 0% to 80%. Modifies $r_{\text{tax}}$ instantly.
   > - Dragon Attack Event: Sets Health Potion supply to 2 and base price to 35.0 Gold.
   > - Gold Rush Event: Immediately adds +100 Gold to all agent accounts."
   >
   > "VAL-01: Engine completes tick in $<2.0$ seconds.
   > VAL-02: GM increases tax to 50%. Agents log 'HOLD' or complaints about high taxes in reasoning.
   > VAL-03: Event triggered via UI. Potion price spikes above 25.0 Gold; News headline triggers alert.
   > VAL-04: LLM returns non-JSON text. System falls back gracefully to 'HOLD' without crashing loop."
5. `ORIGINAL_REQUEST.md` (lines 19-49, 52-70):
   > "R1: Deterministic Market & State Store (`src/`): P_new = max(1.0, P_old * (1 + k * Delta D)), default k = 0.05, min floor 1.0 Gold. Items: 'Health Potion', 'Iron Sword', 'Raw Gem'. Tax T = P_unit * r_tax. Validate agent gold/inventory constraints.
   > R2: Concurrently via asyncio.gather(). Automatic simulated heuristic fallback mode when API keys are absent, network calls fail, or execution times out (>2.0s), safely falling back to 'HOLD'.
   > R3: Endpoints: GET /state, POST /simulation/tick, POST /simulation/start, POST /simulation/stop, POST /policy/tax (0%-80%), POST /policy/event ('Dragon Attack', 'Gold Rush').
   > Acceptance Criteria: Out-of-the-box simulated fallback mode without requiring any API keys. Timing under 2.0s."
6. Workspace Files Check:
   - `specs/features/phase1_mvp.md`, `specs/features/phase2_analytics.md`, and `src/README.md` are present as empty marker files (0 bytes).
   - Git repository is not initialized (`fatal: not a git repository`).

### 2. Logic Chain
1. **Mathematical Price Discovery Chain**:
   - From `feature_specification_mvp_engine_dashboard (1).md:15` and `ORIGINAL_REQUEST.md:21`, price discovery is strictly $P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + k \cdot \Delta D))$.
   - Net demand $\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$ must be calculated solely from validated, successful trades executed during the tick. Failed or invalid trades cannot be counted in $\Delta D$, otherwise failed attempts would distort market pricing.
   - The parameter $k = 0.05$ means each unit of net demand changes the price by $5\%$.
   - The outer function $\max(1.0, \dots)$ is a hard invariant preventing negative or zero prices under severe sell volume (e.g. $\Delta D \le -20$).
2. **Item Catalog and Inventory Boundaries Chain**:
   - From `feature_specification_mvp_engine_dashboard (1).md:46` and `ORIGINAL_REQUEST.md:22`, the supported items are strictly `"Health Potion"`, `"Iron Sword"`, and `"Raw Gem"`.
   - Default base prices are not rigidly locked in the constitution except for Dragon Attack setting Health Potion base price to 35.0 Gold, while VAL-03 implies normal baseline is $< 25.0$ Gold. Sensible defaults are Health Potion: 15.0–20.0 Gold, Iron Sword: 25.0–30.0 Gold, Raw Gem: 10.0–15.0 Gold.
   - Market supply must be tracked because Dragon Attack explicitly sets Health Potion market supply to 2 (`feature_specification_mvp_engine_dashboard (1).md:56`). If supply drops to 0, subsequent buy attempts must fail validation or cap to available units.
3. **Taxation and Constraint Enforcement Chain**:
   - From `feature_specification_mvp_engine_dashboard (1).md:25` and `ORIGINAL_REQUEST.md:23`, $T = P_{\text{unit}} \cdot r_{\text{tax}}$, where $0.0 \le r_{\text{tax}} \le 0.80$.
   - When an agent purchases an item, total required gold is $Q \cdot (P_{\text{unit}} + T)$ or $Q \cdot P_{\text{unit}} \cdot (1 + r_{\text{tax}})$. The validation rule requires: $\text{agent.gold} \ge Q \cdot P_{\text{unit}} \cdot (1 + r_{\text{tax}})$.
   - When selling, the agent must possess $\text{inventory}[item] \ge Q$.
   - If an agent fails either constraint, the trade is rejected, leaving the state pristine.
4. **Policy Shocks Chain**:
   - `POST /policy/event` triggers either `"Dragon Attack"` or `"Gold Rush"`.
   - `"Dragon Attack"` sets `state.items["Health Potion"].supply = 2` and `state.items["Health Potion"].price = 35.0`.
   - `"Gold Rush"` executes an iteration over all agents in the store: $\text{agent.gold} \mathrel{+}= 100.0$.
   - `POST /policy/tax` updates `state.tax_rate` to the requested float, clamped to $[0.0, 0.80]$, which takes effect on the next tick's transactions.

### 3. Caveats
- **Crafting Action**: The JSON schema includes `"CRAFT"` in `action: enum ["BUY", "SELL", "CRAFT", "HOLD"]`. However, the specifications do not define crafting recipes, reagent inputs, or crafting outputs for MVP Phase 1. For Phase 1, `CRAFT` can either be handled as a no-op fallback (`HOLD`) or a simple recipe if specified in Phase 2.
- **Tax Recipient**: The specifications state that tax $T$ is deducted, but do not specify whether collected tax goes to a central "treasury" balance or is burned/removed from circulation. Having an optional `treasury` counter in the state snapshot is recommended.
- **Latency Cutoff**: `tech_stack_specification.md:17` mentions a 2.5s fallback threshold, whereas `ORIGINAL_REQUEST.md:32, 60` and `feature_specification_mvp_engine_dashboard (1).md:65` specify $< 2.0$s. The $2.0$s threshold in `ORIGINAL_REQUEST.md` is authoritative.

### 4. Conclusion
The specification for Core Market Math, Policy Shocks, and State Invariants is complete, consistent, and fully mined:
1. **Market Math**: Strictly deterministic using $P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + 0.05 \cdot (Q_{\text{bought}} - Q_{\text{sold}})))$ with 1.0 Gold floor.
2. **Items**: 3 items ("Health Potion", "Iron Sword", "Raw Gem") with tracked market supply and agent inventories.
3. **Taxes**: $T = P_{\text{unit}} \cdot r_{\text{tax}}$ with $r_{\text{tax}} \in [0.0, 0.80]$, updated instantly via `POST /policy/tax`.
4. **Shocks**: "Dragon Attack" (supply = 2, price = 35.0) and "Gold Rush" (+100 Gold to all agents) via `POST /policy/event`.
5. **State Safety**: Atomic validation checks preventing negative gold, negative inventory, or invalid actions, with graceful fallback to "HOLD".

### 5. Verification Method
To independently verify this specification extraction:
1. Inspect `ORIGINAL_REQUEST.md` lines 19–41, 52–66.
2. Inspect `specs/features/feature_specification_mvp_engine_dashboard (1).md` lines 12–26, 39–58, 63–69.
3. Inspect `specs/constitution/tech_stack_specification.md` lines 14–18.
4. When test suite is executed in subsequent implementation milestones:
   - Price floor test: verify $P_{\text{new}} \ge 1.0$ when $\Delta D = -100$.
   - Tax test: verify tax calculation at $r_{\text{tax}} = 0.0$, $0.2$, $0.5$, $0.8$.
   - Event shock test: verify state mutation after calling `POST /policy/event` for Dragon Attack and Gold Rush.
   - Validation test: attempt BUY with insufficient gold and SELL with insufficient inventory, confirming state invariance.
