# Test Infrastructure & Specification Guide: AI-Driven Game Economy Simulator

## 1. Test Philosophy & Architecture

The test suite for Phase 1 of the **AI-Driven Game Economy Simulator** is designed as an **opaque-box, contract-driven verification harness**. It treats the simulation engine, agent logic, and REST API as deterministic state machines governed strictly by mathematical formulas and interface contracts defined in `PROJECT.md` and `ORIGINAL_REQUEST.md`.

### Core Testing Tenets:
1. **Opaque-Box Contract Enforcement**: Tests interact strictly via public interfaces (`src.models`, `src.market`, `src.agents`, `src.simulation`, `src.main`) without relying on private implementation details.
2. **Deterministic Mathematical Oracles**: Pricing formulas, tax rates, and inventory constraints are verified against closed-form mathematical solutions ($P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + k \cdot \Delta D))$ and $T = P_{\text{unit}} \cdot Q \cdot r_{\text{tax}}$).
3. **Fail-Safe Robustness**: LLM interactions, network failures, malformed JSON, and timeouts ($>2.0\text{s}$) must never crash the tick loop; they must deterministically fall back to `HOLD`.
4. **Hermetic State Isolation**: Every test initializes isolated mock state fixtures to prevent cross-test state leakage or race conditions.
5. **Multi-Tier Testing Pyramid**:
   - **Tier 1 (Feature Isolation)**: Verifies each discrete feature in isolation with $\ge 5$ test cases per feature.
   - **Tier 2 (Boundary & Corner Cases)**: Verifies edge boundaries ($\Delta D \le -20$, $\Delta D = 0$, $r_{\text{tax}} \in \{0.0, 0.80\}$, exact gold, fractional deficit, inventory limits, quantity $[1, 10]$, reasoning length $\le 120$, timeout $>2.0$s) with $\ge 5$ tests per boundary.
   - **Tier 3 (Pairwise Interactions)**: Verifies combinatorial multi-feature couplings (e.g. Dragon Attack + bankrupt agent, 80% tax + bulk purchase, Gold Rush + aggressive buyer, concurrent agent timeout + success).
   - **Tier 4 (Multi-Turn Scenarios)**: Verifies realistic 5-tick continuous trading cycles, macroeconomic policy shocks, shock recoveries, and wealth injections.

---

## 2. Feature Inventory Coverage Matrix

| Feature # | Feature Name | Tier 1 Tests | Tier 2 Boundaries | Tier 3 Pairwise | Tier 4 Scenarios | Status |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | Net Demand Calculation ($\Delta D$) | `test_net_demand_*` (5 tests) | `test_boundary_net_demand_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 2 | Algorithmic Price Discovery | `test_pricing_formula_*` (5 tests) | `test_boundary_pricing_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 3 | Minimum Price Floor Enforcement (1.0) | `test_price_floor_*` (5 tests) | `test_boundary_price_floor_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 4 | Supported Item Catalog (3 items) | `test_item_catalog_*` (5 tests) | `test_boundary_catalog_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 5 | Market Inventory Tracking | `test_market_inventory_*` (5 tests) | `test_boundary_inventory_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 6 | Transaction Tax Calculation | `test_tax_calculation_*` (5 tests) | `test_boundary_tax_rates_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 7 | Buyer Gold Validation | `test_buyer_gold_validation_*` (5 tests) | `test_boundary_buyer_gold_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 8 | Seller Inventory Validation | `test_seller_inventory_validation_*` (5 tests) | `test_boundary_seller_inventory_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 9 | Atomic State Finalization | `test_atomic_execution_*` (5 tests) | `test_boundary_atomic_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 10 | Persona: Garrick the Greedy | `test_persona_garrick_*` (5 tests) | `test_boundary_persona_behavior_*` | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 11 | Persona: Cora the Farmer | `test_persona_cora_*` (5 tests) | `test_boundary_persona_behavior_*` | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 12 | Persona: Boran the Adventurer | `test_persona_boran_*` (5 tests) | `test_boundary_persona_behavior_*` | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 13 | Multi-Provider LLM Engine | `test_llm_provider_*` (5 tests) | Covered in `test_boundary_timeout_*` | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 14 | Structured JSON Schema Enforcement | `test_json_schema_*` (5 tests) | `test_boundary_schema_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 15 | Parallel Agent Concurrency | `test_concurrency_*` (5 tests) | `test_boundary_concurrency_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 16 | Simulated Heuristic Fallback (to HOLD) | `test_heuristic_fallback_*` (5 tests) | `test_boundary_fallback_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 17 | In-Memory State Store | `test_state_store_*` (5 tests) | Covered in `test_boundary_state_*` | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 18 | Manual Single-Tick Stepping (`POST /simulation/tick`) | `test_endpoint_tick_*` (5 tests) | Covered in `test_boundary_tick_*` | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 19 | Background Loop Execution (`/start`, `/stop`) | `test_endpoint_loop_*` (5 tests) | Covered in `test_boundary_loop_*` | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 20 | State Inspection Endpoint (`GET /state`) | `test_endpoint_state_*` (5 tests) | Covered in `test_boundary_state_*` | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 21 | Tax Policy API (`POST /policy/tax`) | `test_endpoint_policy_tax_*` (5 tests) | `test_boundary_tax_policy_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 22 | Shock: Dragon Attack | `test_policy_dragon_attack_*` (5 tests) | `test_boundary_dragon_attack_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 23 | Shock: Gold Rush | `test_policy_gold_rush_*` (5 tests) | `test_boundary_gold_rush_*` (5 tests) | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |
| 24 | Real-Time State Streaming (`/ws`) | `test_websocket_streaming_*` (5 tests) | Covered in `test_boundary_ws_*` | Covered in `test_pairwise_*` | Covered in `test_scenario_*` | Complete |

---

## 3. Test Runner Invocation

### Requirements
Ensure dependencies from `requirements.txt` are installed:
```bash
pip install -r requirements.txt
```

### Full Test Suite Execution
```bash
pytest tests/ -v
```

### Tier-by-Tier Execution
```bash
# Tier 1: Feature Isolation
pytest tests/test_tier1_features.py -v

# Tier 2: Boundary & Corner Cases
pytest tests/test_tier2_boundaries.py -v

# Tier 3: Pairwise Interactions
pytest tests/test_tier3_pairwise.py -v

# Tier 4: Multi-Turn Scenarios
pytest tests/test_tier4_scenarios.py -v
```

### Pytest Configuration Flags
- `-v`: Verbose output with individual test names
- `--asyncio-mode=auto`: Automatic handling of coroutine tests
- `-s`: (Optional) Disable stdout capture for debugging logs
- `--tb=short`: Concise traceback presentation on assertions

---

## 4. Pass / Fail Semantics & Invariants

A test run is considered passing if and only if **100% of all test cases pass cleanly without errors or warnings**.

### Critical State Invariants Checked Across All Tiers:
1. **Price Floor Invariant**: For any item $i$, $\text{price}_i \ge 1.0$ Gold at all times.
2. **Non-Negative Wealth Invariant**: For any agent $a$, $\text{gold}_a \ge 0.0$ at all times.
3. **Non-Negative Inventory Invariant**: For any agent $a$ and item $i$, $\text{inventory}_a[i] \ge 0$ at all times.
4. **Market Supply Conservation**: For any item $i$, $\text{market\_supply}_i \ge 0$.
5. **Net Demand Zero-Sum Invariance**: If an agent buys $Q$ units from market, market supply drops by $Q$ and buyer inventory increments by $Q$.
6. **Tax Clamping Invariant**: $r_{\text{tax}} \in [0.0, 0.80]$. Any input $< 0.0$ or $> 0.80$ is clamped or rejected.
7. **Graceful Degradation Invariant**: If an LLM call exceeds $2.0$ seconds or outputs malformed data, decision must be `action="HOLD"` without crashing the engine.
8. **Deterministic Rounding**: All monetary calculations and state prices are rounded to 2 decimal places to prevent float precision drift.
