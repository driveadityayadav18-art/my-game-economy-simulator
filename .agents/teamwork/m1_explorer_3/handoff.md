# Unit Testing Strategy & Verification Specification (Milestone 1)

**Agent**: `teamwork_preview_explorer` (M1 Explorer 3: Verification & Unit Testing)  
**Working Directory**: `c:\Users\Aditya S Yadav\Desktop\anything-to-website\my-game-economy-simulator\.agents\teamwork\m1_explorer_3`  
**Milestone**: Milestone 1 (Deterministic Market & State Store)  
**Target Modules**: `src/config.py`, `src/models.py`, `src/market.py`  
**Date**: 2026-09-27  

---

## 1. Observation

Direct observations and quotations from authoritative project specifications and contracts:

### 1.1 Pricing Math & Floor Enforcement
- **`ORIGINAL_REQUEST.md` (lines 20-21)**:
  > "Calculate price adjustments based on net demand ($\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$) using $P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + k \cdot \Delta D))$ with default sensitivity $k = 0.05$ and minimum price floor of $1.0$ Gold."
- **`ORIGINAL_REQUEST.md` (line 53)**:
  > "Item prices update deterministically following $P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + k \cdot \Delta D))$ and never drop below $1.0$ Gold."
- **`specs/features/feature_specification_mvp_engine_dashboard (1).md` (lines 13-21)**:
  > "$$P_{\text{new}} = \max\left(1.0, P_{\text{old}} \cdot \left(1 + k \cdot \Delta D\right)\right)$$
  > Where:
  > - $P_{\text{old}}$ = Current price of item
  > - $k$ = Sensitivity coefficient (default: $0.05$)
  > - $\Delta D$ = Net transaction quantity in current tick
  > - Minimum price bound = $1.0$ Gold"
- **`PROJECT.md` (lines 40-41, 138-140)**:
  > "Feature 2: Algorithmic Price Discovery — Adjusts item prices via $P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + k \cdot \Delta D))$ ($k=0.05$)"
  > "Feature 3: Minimum Price Floor Enforcement — Guarantees price never drops below 1.0 Gold under heavy sell pressure"
  > ```python
  > def calculate_new_price(old_price: float, net_demand: int, k: float = 0.05, min_price: float = 1.0) -> float:
  >     """Computes P_new = max(min_price, old_price * (1 + k * net_demand)). Rounded to 2 decimals."""
  > ```

### 1.2 Taxation Math
- **`ORIGINAL_REQUEST.md` (line 23)**:
  > "Calculate transaction taxes $T = P_{\text{unit}} \cdot r_{\text{tax}}$ and validate agent gold/inventory constraints before finalizing transactions."
- **`specs/features/feature_specification_mvp_engine_dashboard (1).md` (lines 23-25)**:
  > "Tax deduction formula for transactions:
  > $$T = P_{\text{unit}} \cdot r_{\text{tax}}$$"
- **`PROJECT.md` (lines 44, 142-144)**:
  > "Feature 6: Transaction Tax Calculation — Calculates transaction tax $T = P_{\text{unit}} \cdot r_{\text{tax}}$ ($0.0 \le r_{\text{tax}} \le 0.80$)"
  > ```python
  > def calculate_tax(unit_price: float, quantity: int, tax_rate: float) -> float:
  >     """Computes T = unit_price * quantity * tax_rate. Rounded to 2 decimals."""
  > ```

### 1.3 Validation Invariants & Atomic Execution
- **`ORIGINAL_REQUEST.md` (line 55)**:
  > "Insufficient gold or inventory prevents invalid trades without corrupting state."
- **`PROJECT.md` (lines 45-47, 146-152)**:
  > "Feature 7: Buyer Gold Validation — Prevents purchases when agent gold $< Q \cdot P_{\text{unit}} \cdot (1 + r_{\text{tax}})$"
  > "Feature 8: Seller Inventory Validation — Prevents sales when agent inventory $< Q$"
  > "Feature 9: Atomic State Finalization — Commits balances, inventory, and logs only when all validation checks pass"
  > ```python
  > def validate_transaction(agent: AgentState, item: ItemState, action: ActionType, quantity: int, tax_rate: float) -> tuple[bool, str]:
  >     """Validates buyer gold or seller inventory constraints."""
  >
  > def execute_transaction(state: EconomyState, agent_name: str, decision: AgentDecision) -> TransactionRecord:
  >     """Executes validated transaction atomically against EconomyState."""
  > ```

### 1.4 Macroeconomic Shocks
- **`ORIGINAL_REQUEST.md` (lines 40, 63-64)**:
  > "POST /policy/event: Triggers economic shock events ('Dragon Attack': Health Potion supply = 2, base price = 35.0 Gold; 'Gold Rush': +100 Gold credited to all agents)."
  > "Dragon Attack shock sets Health Potion supply to 2 and base price to 35.0 Gold."
  > "Gold Rush shock immediately increments each agent's gold balance by +100."
- **`PROJECT.md` (lines 60-61, 154-160)**:
  > "Feature 22: Shock: Dragon Attack — POST /policy/event sets Health Potion supply = 2, base price = 35.0 Gold"
  > "Feature 23: Shock: Gold Rush — POST /policy/event credits +100 Gold immediately to all active agents"

### 1.5 Target Module Configurations & Pydantic Data Models
- **`PROJECT.md` (lines 83-134)**:
  > Defines `ActionType` enum (`BUY`, `SELL`, `HOLD`, `CRAFT`), `AgentDecision` (`action`, `item`, `quantity` 1..10, `reasoning` max 120), `ItemState` (`price` ge=1.0, `supply` ge=0), `AgentState` (`gold` ge=0.0, `inventory`), `TransactionRecord` (`tick`, `agent_name`, `action`, `item`, `quantity`, `unit_price`, `tax_paid`, `total_cost`, `status`, `reason`), `EconomyState` (`tax_rate` 0.0..0.80, `items`, `agents`, `recent_transactions`).
- **`m1_explorer_1/DISPATCH.md` (lines 16-27)**:
  > `src/config.py` constants: `SIMULATION_TICK_INTERVAL` (4.0s), `LLM_TIMEOUT_SECONDS` (2.0s), `DEFAULT_TAX_RATE` (0.10), `MIN_TAX_RATE` (0.0), `MAX_TAX_RATE` (0.80), `PRICE_SENSITIVITY_K` (0.05), `PRICE_FLOOR` (1.0).
  > Default items: "Health Potion" (price=20.0, supply=100), "Iron Sword" (price=30.0, supply=100), "Raw Gem" (price=15.0, supply=100).
  > Default agents: Garrick (150 gold), Cora (60 gold), Boran (40 gold).

---

## 2. Logic Chain

From the observed requirements and interface contracts, we construct a rigorous verification logic chain:

### 2.1 Price Discovery Logic & Boundary Proofs
1. **Neutral Net Demand ($\Delta D = 0$)**:
   - $P_{\text{new}} = \max(1.0, \text{round}(P_{\text{old}} \cdot (1 + 0.05 \cdot 0), 2)) = P_{\text{old}}$.
   - Tested on baseline prices $20.0, 1.0, 35.5, 100.0$.
   - Proves price stability when buy and sell orders cancel out or when agents choose `HOLD`.
2. **Positive Net Demand ($\Delta D > 0$)**:
   - Each net unit bought scales price up by $k = 0.05$ ($5\%$).
   - For $P_{\text{old}} = 20.0$:
     - $\Delta D = 1 \implies 20.0 \cdot 1.05 = 21.00$
     - $\Delta D = 2 \implies 20.0 \cdot 1.10 = 22.00$
     - $\Delta D = 5 \implies 20.0 \cdot 1.25 = 25.00$
     - $\Delta D = 10 \implies 20.0 \cdot 1.50 = 30.00$
   - Fractional float check: $15.0 \cdot (1 + 0.05 \cdot 3) = 15.0 \cdot 1.15 = 17.25$.
   - Rounding check: $13.33 \cdot 1.05 = 13.9965 \implies 14.00$.
3. **Negative Net Demand ($\Delta D < 0$)**:
   - Each net unit sold scales price down by $5\%$.
   - For $P_{\text{old}} = 20.0$:
     - $\Delta D = -1 \implies 20.0 \cdot 0.95 = 19.00$
     - $\Delta D = -2 \implies 20.0 \cdot 0.90 = 18.00$
     - $\Delta D = -5 \implies 20.0 \cdot 0.75 = 15.00$
4. **Price Floor Clamping Proof ($\Delta D \le -20$)**:
   - At $\Delta D = -20$, multiplier is $1 + 0.05(-20) = 0.0$. Raw price is $0.0$. $\max(1.0, 0.0) = 1.0$.
   - At $\Delta D = -25$, multiplier is $-0.25$. Raw price is negative. $\max(1.0, -5.0) = 1.0$.
   - Under extreme panic selling ($\Delta D = -100$), $P_{\text{raw}} = 100.0 \cdot (1 - 5.0) = -400.0$. $\max(1.0, -400.0) = 1.0$.
   - Invariant: $P_{\text{new}} \ge 1.0$ holds for all $\Delta D \in (-\infty, \infty)$.

### 2.2 Tax Calculation Logic
1. **Formula**: $T = \text{round}(P_{\text{unit}} \cdot Q \cdot r_{\text{tax}}, 2)$.
2. **Across Regulatory Rates**:
   - $r_{\text{tax}} = 0.0$: Tax is identically $0.00$. Total buyer cost equals gross price $P_{\text{unit}} \cdot Q$.
   - $r_{\text{tax}} = 0.10$ (default): $20.0 \cdot 1 \cdot 0.10 = 2.00$; $20.0 \cdot 3 \cdot 0.10 = 6.00$.
   - $r_{\text{tax}} = 0.50$: $20.0 \cdot 1 \cdot 0.50 = 10.00$; $35.0 \cdot 2 \cdot 0.50 = 35.00$.
   - $r_{\text{tax}} = 0.80$ (maximum): $20.0 \cdot 1 \cdot 0.80 = 16.00$; $10.0 \cdot 5 \cdot 0.80 = 40.00$.
3. **Safety Guards**: $Q \le 0$, $P_{\text{unit}} \le 0$, or $r_{\text{tax}} \le 0$ must return $0.0$ to prevent negative tax or accounting distortions.

### 2.3 Trade Validation & Solvency Logic
1. **BUY Constraint Check**:
   - Preconditions: Item exists in market, quantity $\ge 1$, $\text{item.supply} \ge Q$, $\text{agent.gold} + 10^{-7} \ge \text{total\_cost} = Q \cdot P_{\text{unit}} + T$.
   - **Exact Gold**: $\text{agent.gold} == \text{total\_cost}$. Agent spends every coin; balance becomes $0.00$. Validation returns `(True, "BUY transaction valid.")`.
   - **Surplus Gold**: $\text{agent.gold} > \text{total\_cost}$. Validation returns `True`.
   - **Deficient Gold**: $\text{agent.gold} < \text{total\_cost}$. Even a deficit of $0.01$ Gold triggers rejection `(False, "Insufficient gold...")`.
   - **Deficient Supply**: $\text{item.supply} < Q$. Even if agent has infinite gold, order is rejected `(False, "Insufficient market supply...")`.
2. **SELL Constraint Check**:
   - Preconditions: Item exists, quantity $\ge 1$, $\text{agent.inventory}[item] \ge Q$.
   - **Exact Inventory**: Agent holds exactly $Q$ units. Validation returns `True`.
   - **Surplus Inventory**: Agent holds $> Q$ units. Validation returns `True`.
   - **Deficient Inventory**: Agent holds $< Q$ units (or $0$ units). Validation returns `(False, "Insufficient inventory...")`.
3. **HOLD / CRAFT Check**:
   - Always returns `True`; requires no gold, inventory, or item lookup.

### 2.4 State Atomicity & Invariant Preservation
1. When a transaction succeeds:
   - For `BUY`: `agent.gold` decremented by `total_cost`, `agent.inventory[item]` incremented by $Q$, `item.supply` decremented by $Q$. Emits `status="EXECUTED"`.
   - For `SELL`: `agent.gold` incremented by $Q \cdot P_{\text{unit}}$, `agent.inventory[item]` decremented by $Q$, `item.supply` incremented by $Q$. Emits `status="EXECUTED"`.
2. When a transaction fails:
   - Rejected trades must **never mutate any state**: agent gold balance is unchanged, agent inventory is unchanged, market supply is unchanged.
   - Emits `status="REJECTED"` with diagnostic reason recorded in `state.recent_transactions`.
   - Net demand $\Delta D$ ignores `REJECTED` trades so failed transactions do not skew market prices.

### 2.5 Policy Shock Mutators
1. **Dragon Attack**:
   - Health Potion supply is set to exactly 2.
   - Health Potion price is set to exactly 35.0 Gold.
   - Invariant: Other items ("Iron Sword", "Raw Gem") and all agent balances remain untouched.
   - Idempotent: Executing multiple times repeatedly preserves supply = 2 and price = 35.0.
2. **Gold Rush**:
   - Every active agent receives $+100.0$ Gold credited to their balance: `agent.gold = round(agent.gold + 100.0, 2)`.
   - Invariant: Market supplies and prices remain untouched.

---

## 3. Caveats

1. **Test Colocation vs Agent Directory**:
   - Under the teamwork rules, agents only write inside `.agents/teamwork/<agent_dir>/`. Therefore, executable proposed test files have been placed directly in `.agents/teamwork/m1_explorer_3/`:
     - `proposed_test_market.py`
     - `proposed_test_models.py`
     - `proposed_test_config.py`
   - When `m1_worker` implements Milestone 1, they should copy these into `tests/test_market.py`, `tests/test_models.py`, `tests/test_config.py` (or execute them directly with pytest).
2. **E2E Test Track Synergy**:
   - `test_writer_track` is generating the 4-tier E2E opaque-box suite (`test_tier1_features.py` through `test_tier4_scenarios.py`).
   - The test specifications designed here for Milestone 1 are dedicated **white-box / unit-level tests** targeting `src/config.py`, `src/models.py`, and `src/market.py` directly. They execute in < 0.2 seconds and provide immediate feedback for the worker without requiring the entire FastAPI or LLM mock stack.
3. **Floating Point Rounding**:
   - Standard IEEE 754 floating point arithmetic introduces representation artifacts (e.g. `20.0 * 1.05 = 21.000000000000004` or `15.0 - 0.75 = 14.25`). All pricing, tax, and balance calculations must explicitly invoke `round(val, 2)`.
   - Solvency validation utilizes an epsilon tolerance of $+10^{-7}$ Gold (`round(agent.gold, 2) + 1e-7 >= total_cost`) to prevent false-negative rejections.

---

## 4. Conclusion

The testing strategy and verification specifications for Milestone 1 are fully formulated, mathematically rigorous, and delivered with ready-to-run unit test implementations.

### 4.1 Unit Test Inventory Overview

| Test Module | Test Class | Test Function | Target Feature | Verification Criteria |
| :--- | :--- | :--- | :--- | :--- |
| `test_market.py` | `TestPriceDiscovery` | `test_price_discovery_zero_demand` | Feature 1 & 2 | Price invariant when $\Delta D = 0$ across multiple price points |
| `test_market.py` | `TestPriceDiscovery` | `test_price_discovery_positive_demand` | Feature 2 | $P_{\text{new}} = P_{\text{old}} \cdot (1 + 0.05 \cdot \Delta D)$ for $\Delta D \in [1, 10]$ |
| `test_market.py` | `TestPriceDiscovery` | `test_price_discovery_negative_demand` | Feature 2 | $P_{\text{new}} = P_{\text{old}} \cdot (1 - 0.05 \cdot \|\Delta D\|)$ for negative demand |
| `test_market.py` | `TestPriceDiscovery` | `test_price_floor_enforcement_at_multiplier_zero` | Feature 3 | $\Delta D = -20 \implies \text{price} = 1.0$ Gold |
| `test_market.py` | `TestPriceDiscovery` | `test_price_floor_enforcement_at_negative_multiplier` | Feature 3 | $\Delta D = -25 \implies \text{price} = 1.0$ Gold |
| `test_market.py` | `TestPriceDiscovery` | `test_price_floor_extreme_negative_demand` | Feature 3 | $\Delta D = -100$ and $-1000 \implies \text{price} = 1.0$ Gold strictly |
| `test_market.py` | `TestPriceDiscovery` | `test_price_floor_already_at_minimum` | Feature 3 | $P_{\text{old}} = 1.0, \Delta D = -50 \implies \text{price} = 1.0$ Gold |
| `test_market.py` | `TestPriceDiscovery` | `test_price_floor_custom_bound` | Feature 3 | `min_price = 5.0` respected |
| `test_market.py` | `TestPriceDiscovery` | `test_price_rounding_precision` | Feature 2 | 2-decimal rounding precision ($13.33 \to 14.00$) |
| `test_market.py` | `TestTaxCalculation` | `test_tax_rate_zero_percent` | Feature 6 | $r_{\text{tax}} = 0.0 \implies T = 0.0$ |
| `test_market.py` | `TestTaxCalculation` | `test_tax_rate_ten_percent` | Feature 6 | $r_{\text{tax}} = 0.10 \implies T = \text{round}(P \cdot Q \cdot 0.10, 2)$ |
| `test_market.py` | `TestTaxCalculation` | `test_tax_rate_fifty_percent` | Feature 6 | $r_{\text{tax}} = 0.50 \implies T = \text{round}(P \cdot Q \cdot 0.50, 2)$ |
| `test_market.py` | `TestTaxCalculation` | `test_tax_rate_eighty_percent` | Feature 6 | $r_{\text{tax}} = 0.80 \implies T = \text{round}(P \cdot Q \cdot 0.80, 2)$ |
| `test_market.py` | `TestTaxCalculation` | `test_tax_fractional_rounding` | Feature 6 | Correct rounding on half-cents ($1.525 \to 1.53/1.52$) |
| `test_market.py` | `TestTaxCalculation` | `test_tax_zero_or_negative_guards` | Feature 6 | Guard against $Q \le 0, P \le 0, r_{\text{tax}} \le 0 \implies 0.0$ |
| `test_market.py` | `TestTransactionValidation` | `test_buy_validation_exact_gold` | Feature 7 | Agent gold exactly matches total cost $\implies$ Valid |
| `test_market.py` | `TestTransactionValidation` | `test_buy_validation_surplus_gold` | Feature 7 | Agent gold exceeds total cost $\implies$ Valid |
| `test_market.py` | `TestTransactionValidation` | `test_buy_validation_deficient_gold` | Feature 7 | Agent short by $0.01$ Gold $\implies$ Rejected |
| `test_market.py` | `TestTransactionValidation` | `test_buy_validation_insufficient_market_supply` | Feature 5 & 7 | Market supply $<$ quantity $\implies$ Rejected |
| `test_market.py` | `TestTransactionValidation` | `test_buy_validation_exact_market_supply` | Feature 5 & 7 | Market supply == quantity $\implies$ Valid |
| `test_market.py` | `TestTransactionValidation` | `test_buy_validation_missing_item` | Feature 4 & 7 | item=None on BUY $\implies$ Rejected |
| `test_market.py` | `TestTransactionValidation` | `test_sell_validation_exact_inventory` | Feature 8 | Inventory == quantity $\implies$ Valid |
| `test_market.py` | `TestTransactionValidation` | `test_sell_validation_surplus_inventory` | Feature 8 | Inventory $>$ quantity $\implies$ Valid |
| `test_market.py` | `TestTransactionValidation` | `test_sell_validation_deficient_inventory` | Feature 8 | Inventory $<$ quantity $\implies$ Rejected |
| `test_market.py` | `TestTransactionValidation` | `test_sell_validation_zero_inventory` | Feature 8 | Inventory == 0 $\implies$ Rejected |
| `test_market.py` | `TestTransactionValidation` | `test_hold_validation_always_valid` | Feature 9 | HOLD requires no items/funds $\implies$ Valid |
| `test_market.py` | `TestTransactionValidation` | `test_craft_validation_falls_back_to_hold` | Feature 9 | CRAFT treated as HOLD in Phase 1 $\implies$ Valid |
| `test_market.py` | `TestAtomicExecution` | `test_atomic_buy_success` | Feature 9 | Gold deducted, inventory added, supply decremented, EXECUTED |
| `test_market.py` | `TestAtomicExecution` | `test_atomic_buy_rejected_insufficient_gold` | Feature 9 | Rejection leaves gold, inventory, and supply 100% pristine |
| `test_market.py` | `TestAtomicExecution` | `test_atomic_sell_success` | Feature 9 | Inventory deducted, gold added, supply incremented, EXECUTED |
| `test_market.py` | `TestAtomicExecution` | `test_atomic_sell_rejected_insufficient_inventory` | Feature 9 | Rejection leaves inventory and gold untouched |
| `test_market.py` | `TestAtomicExecution` | `test_atomic_hold_execution` | Feature 9 | Emits EXECUTED record with zero financial cost |
| `test_market.py` | `TestAtomicExecution` | `test_atomic_unknown_agent_rejection` | Feature 9 | Nonexistent agent rejected without corrupting store |
| `test_market.py` | `TestAtomicExecution` | `test_atomic_unknown_item_rejection` | Feature 4 & 9 | Non-catalog item rejected cleanly |
| `test_market.py` | `TestNetDemandAndPriceUpdates` | `test_net_demand_calculation` | Feature 1 | Sums executed BUY minus executed SELL; ignores rejected |
| `test_market.py` | `TestNetDemandAndPriceUpdates` | `test_update_market_prices` | Feature 2 | Batch updates all commodities according to tick trades |
| `test_market.py` | `TestMacroeconomicShocks` | `test_apply_dragon_attack` | Feature 22 | Sets Health Potion supply = 2, price = 35.0; other items intact |
| `test_market.py` | `TestMacroeconomicShocks` | `test_apply_dragon_attack_idempotent` | Feature 22 | Calling shock multiple times repeatedly resets supply/price |
| `test_market.py` | `TestMacroeconomicShocks` | `test_apply_gold_rush_default` | Feature 23 | Credits $+100.0$ Gold to every active agent; items intact |
| `test_market.py` | `TestMacroeconomicShocks` | `test_apply_gold_rush_custom_amount` | Feature 23 | Credits custom amount (e.g. $+50.0$ Gold) |
| `test_models.py` | `TestActionTypeEnum` | `test_action_enum_values` | Schema | BUY, SELL, HOLD, CRAFT string matching |
| `test_models.py` | `TestAgentDecisionModel` | `test_quantity_lower_boundary_one` | Schema | quantity=1 is valid boundary |
| `test_models.py` | `TestAgentDecisionModel` | `test_quantity_upper_boundary_ten` | Schema | quantity=10 is valid boundary |
| `test_models.py` | `TestAgentDecisionModel` | `test_quantity_zero_raises_validation_error` | Schema | quantity=0 raises ValidationError |
| `test_models.py` | `TestAgentDecisionModel` | `test_quantity_exceeding_ten_raises_validation_error` | Schema | quantity=11 raises ValidationError |
| `test_models.py` | `TestAgentDecisionModel` | `test_reasoning_maximum_length_120` | Schema | 120 chars valid; 121 chars raises ValidationError |
| `test_models.py` | `TestItemStateModel` | `test_item_price_below_floor_raises_validation_error` | Schema | price < 1.0 raises ValidationError |
| `test_models.py` | `TestAgentStateModel` | `test_agent_negative_gold_raises_validation_error` | Schema | gold < 0.0 raises ValidationError |
| `test_models.py` | `TestEconomyStateModel` | `test_tax_rate_minimum_and_maximum_bounds` | Schema | tax_rate in [0.0, 0.80]; outside raises ValidationError |
| `test_config.py` | `TestConfigDefaults` | `test_simulation_tick_interval` | Config | SIMULATION_TICK_INTERVAL == 4.0 |
| `test_config.py` | `TestConfigDefaults` | `test_llm_timeout_seconds` | Config | LLM_TIMEOUT_SECONDS == 2.0 |
| `test_config.py` | `TestConfigDefaults` | `test_price_discovery_parameters` | Config | k == 0.05, min_price == 1.0 |
| `test_config.py` | `TestConfigDefaults` | `test_default_items_catalog` | Config | Health Potion (20.0, 100), Iron Sword (30.0, 100), Raw Gem (15.0, 100) |
| `test_config.py` | `TestConfigDefaults` | `test_default_agents_configuration` | Config | Garrick (150 gold), Cora (60 gold), Boran (40 gold) |
| `test_config.py` | `TestConfigEnvironmentOverrides` | `test_override_tick_interval` | Config | Environment variables override default settings |

---

## 5. Verification Method

### 5.1 Verification Commands for the Worker

When `m1_worker` executes Milestone 1, they must run the following exact verification sequence:

#### Step 1: Environment & Dependency Installation
```bash
# Verify Python version (requires Python 3.11+)
python --version

# Install dependencies
python -m pip install pydantic python-dotenv pytest pytest-asyncio
```

#### Step 2: Running Proposed Unit Tests Directly
The worker can copy the proposed unit tests to `tests/` or execute them directly from `.agents/teamwork/m1_explorer_3/`:
```bash
# Direct run of Milestone 1 unit tests
python -m pytest .agents/teamwork/m1_explorer_3/proposed_test_market.py -v
python -m pytest .agents/teamwork/m1_explorer_3/proposed_test_models.py -v
python -m pytest .agents/teamwork/m1_explorer_3/proposed_test_config.py -v

# Or after placing them in tests/:
python -m pytest tests/test_market.py tests/test_models.py tests/test_config.py -v
```

#### Step 3: Targeted Verification for Specific Features
To isolate specific test groups during implementation:
```bash
# Test Price Discovery & Floor Clamping exclusively
python -m pytest tests/test_market.py -k "TestPriceDiscovery" -v

# Test Tax Rates exclusively (0%, 10%, 50%, 80%)
python -m pytest tests/test_market.py -k "TestTaxCalculation" -v

# Test BUY & SELL validation constraints exclusively
python -m pytest tests/test_market.py -k "TestTransactionValidation" -v

# Test Atomic Execution & Shock Mutators exclusively
python -m pytest tests/test_market.py -k "TestAtomicExecution or TestMacroeconomicShocks" -v
```

#### Step 4: Verification of 100% Pass & Code Coverage
```bash
# Run all Milestone 1 unit tests with coverage reporting
python -m pytest tests/test_market.py tests/test_models.py tests/test_config.py --cov=src.market --cov=src.models --cov=src.config --cov-report=term-missing -v
```

### 5.2 Pass / Invalidation Conditions
- **Pass Condition**:
  - All 50+ unit tests across `test_market.py`, `test_models.py`, and `test_config.py` exit with code `0` (100% passing).
  - No floating point assertion failures or rounding anomalies.
  - Zero unhandled exceptions or state leakage when transactions are rejected.
- **Invalidation Condition**:
  - Any calculated price drops below $1.0$ under negative net demand.
  - Any rejected trade modifies `agent.gold`, `agent.inventory`, or `item.supply`.
  - Tax calculation fails to clamp or round to 2 decimal places.
  - Pydantic models permit invalid quantities ($0$ or $>10$) or out-of-bound tax rates ($<0.0$ or $>0.80$).
