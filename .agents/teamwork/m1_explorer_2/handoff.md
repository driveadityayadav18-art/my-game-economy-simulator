# Technical Design Specification & Exploration Report: Market & Math (`src/market.py`)

**Agent**: `teamwork_preview_explorer` (M1 Explorer 2: Market & Math)  
**Working Directory**: `c:\Users\Aditya S Yadav\Desktop\anything-to-website\my-game-economy-simulator\.agents\teamwork\m1_explorer_2`  
**Milestone**: Milestone 1 (Deterministic Market & State Store)  
**Date**: 2026-09-27  

---

## 1. Observation

Direct observations and citations from authoritative repository sources:

### 1.1 Mathematical Price Discovery Specification
- **`ORIGINAL_REQUEST.md` (lines 20-21)**:
  > "Calculate price adjustments based on net demand ($\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$) using $P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + k \cdot \Delta D))$ with default sensitivity $k = 0.05$ and minimum price floor of $1.0$ Gold."
- **`specs/features/feature_specification_mvp_engine_dashboard (1).md` (lines 13-21)**:
  > "Price adjustments are calculated based on net demand ($\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$) using the following formula:
  > $$P_{\text{new}} = \max\left(1.0, P_{\text{old}} \cdot \left(1 + k \cdot \Delta D\right)\right)$$
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

### 1.2 Taxation Math Specification
- **`ORIGINAL_REQUEST.md` (lines 23, 54)**:
  > "Calculate transaction taxes $T = P_{\text{unit}} \cdot r_{\text{tax}}$ and validate agent gold/inventory constraints before finalizing transactions."
  > "Tax deductions are correctly applied to transactions according to the current tax rate."
- **`specs/features/feature_specification_mvp_engine_dashboard (1).md` (lines 23-25)**:
  > "Tax deduction formula for transactions:
  > $$T = P_{\text{unit}} \cdot r_{\text{tax}}$$"
- **`PROJECT.md` (lines 44, 142-144)**:
  > "Feature 6: Transaction Tax Calculation — Calculates transaction tax $T = P_{\text{unit}} \cdot r_{\text{tax}}$ ($0.0 \le r_{\text{tax}} \le 0.80$)"
  > ```python
  > def calculate_tax(unit_price: float, quantity: int, tax_rate: float) -> float:
  >     """Computes T = unit_price * quantity * tax_rate. Rounded to 2 decimals."""
  > ```

### 1.3 Transaction Validation & Invariants
- **`ORIGINAL_REQUEST.md` (lines 23, 55)**:
  > "validate agent gold/inventory constraints before finalizing transactions."
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
- **`USER_REQUEST` dispatch**:
  > "- Transaction validation rules:
  >    - BUY: checks if buyer has gold >= Q * unit_price + tax and market supply >= Q.
  >    - SELL: checks if seller has inventory[item] >= Q.
  >    - HOLD: always valid, no mutation.
  >  - Atomic trade execution: mutates agent gold/inventory, market supply, records TransactionRecord (EXECUTED or REJECTED)."

### 1.4 Macroeconomic Shock Mutators Specification
- **`ORIGINAL_REQUEST.md` (lines 40, 63-64)**:
  > "POST /policy/event: Triggers economic shock events ('Dragon Attack': Health Potion supply = 2, base price = 35.0 Gold; 'Gold Rush': +100 Gold credited to all agents)."
  > "Dragon Attack shock sets Health Potion supply to 2 and base price to 35.0 Gold."
  > "Gold Rush shock immediately increments each agent's gold balance by +100."
- **`PROJECT.md` (lines 60-61, 154-160)**:
  > "Feature 22: Shock: Dragon Attack — POST /policy/event sets Health Potion supply = 2, base price = 35.0 Gold"
  > "Feature 23: Shock: Gold Rush — POST /policy/event credits +100 Gold immediately to all active agents"
  > ```python
  > def apply_dragon_attack(state: EconomyState) -> None:
  >     """Sets Health Potion supply = 2 and base price = 35.0."""
  >
  > def apply_gold_rush(state: EconomyState, gold_amount: float = 100.0) -> None:
  >     """Credits gold_amount to all agents."""
  > ```

---

## 2. Logic Chain

### 2.1 Price Discovery Derivation & Boundary Proofs

1. **Formula Structure**:
   $$P_{\text{new}} = \max\left(P_{\text{floor}}, \text{round}\left(P_{\text{old}} \cdot (1 + k \cdot \Delta D), 2\right)\right)$$
   Where:
   - $P_{\text{old}}$ is the commodity's current price before tick adjustments ($P_{\text{old}} \ge 1.0$).
   - $k$ is the sensitivity constant ($k = 0.05$).
   - $\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$ is the net transaction volume across all executed trades for the commodity in the tick.
   - $P_{\text{floor}} = 1.0$ Gold is the absolute lower boundary.

2. **Step-by-Step Evaluation**:
   - Step 1: Compute raw scaling multiplier $M = 1.0 + k \cdot \Delta D$.
   - Step 2: Multiply by current price: $P_{\text{raw}} = P_{\text{old}} \cdot M$.
   - Step 3: Apply 2-decimal rounding: $P_{\text{round}} = \text{round}(P_{\text{raw}}, 2)$.
   - Step 4: Enforce minimum price floor: $P_{\text{new}} = \max(P_{\text{floor}}, P_{\text{round}})$.

3. **Mathematical Behavior Across Regimes**:
   - **Neutral Demand ($\Delta D = 0$)**:
     $M = 1 + 0.05 \cdot 0 = 1.0 \implies P_{\text{raw}} = P_{\text{old}} \implies P_{\text{new}} = P_{\text{old}}$. Price is invariant when buying and selling are balanced or when all agents choose `HOLD`.
   - **Positive Demand ($\Delta D > 0$)**:
     For $P_{\text{old}} = 20.0$, $\Delta D = +3$:
     $M = 1 + 0.05 \cdot 3 = 1.15 \implies P_{\text{raw}} = 20.0 \cdot 1.15 = 23.00 \implies P_{\text{new}} = 23.00$.
   - **Moderate Negative Demand ($\Delta D < 0, 1 + k \Delta D > 0$)**:
     For $P_{\text{old}} = 20.0$, $\Delta D = -4$:
     $M = 1 + 0.05 \cdot (-4) = 0.80 \implies P_{\text{raw}} = 20.0 \cdot 0.80 = 16.00 \implies P_{\text{new}} = 16.00$.
   - **Severe Negative Demand ($1 + k \Delta D \le 0$)**:
     If $\Delta D = -20$, $M = 1 - 1.0 = 0.0 \implies P_{\text{raw}} = 0.0$.
     $\max(1.0, 0.0) = 1.0$.
     If $\Delta D = -30$, $M = 1 - 1.5 = -0.5 \implies P_{\text{raw}} = -10.0$.
     $\max(1.0, -10.0) = 1.0$.
   - **Extreme Boundary Proof**:
     Let $\Delta D \to -\infty$. For any $P_{\text{old}} > 0$ and $k > 0$, $P_{\text{raw}} < 0$.
     Because $\max(1.0, P_{\text{raw}}) = 1.0$, $P_{\text{new}}$ is strictly bounded below by $1.0$. The invariant $P_{\text{new}} \ge 1.0$ is guaranteed for all real numbers $\Delta D, P_{\text{old}}, k$.

### 2.2 Tax Mathematics & Financial Settlement

1. **Tax Deduction Formula**:
   $$T = \text{round}\left(P_{\text{unit}} \cdot Q \cdot r_{\text{tax}}, 2\right)$$
   Where:
   - $P_{\text{unit}}$ is the execution unit price.
   - $Q$ is the quantity of units purchased ($Q \ge 1$).
   - $r_{\text{tax}}$ is the active macroeconomic tax rate ($0.0 \le r_{\text{tax}} \le 0.80$).

2. **Settlement Accounting**:
   - **On BUY**:
     - The buyer pays for the commodity plus the transaction tax:
       $$\text{total\_cost} = \text{round}(P_{\text{unit}} \cdot Q + T, 2)$$
     - Buyer's gold is decremented: $\text{agent.gold} \leftarrow \text{agent.gold} - \text{total\_cost}$.
     - Buyer's inventory is incremented: $\text{agent.inventory}[item] \leftarrow \text{agent.inventory}[item] + Q$.
     - Market supply is decremented: $\text{market.supply}[item] \leftarrow \text{market.supply}[item] - Q$.
     - Transaction record logs: $\text{unit\_price} = P_{\text{unit}}$, $\text{tax\_paid} = T$, $\text{total\_cost} = \text{total\_cost}$.
   - **On SELL**:
     - The seller disposes of goods and receives gross market proceeds:
       $$\text{revenue} = \text{round}(P_{\text{unit}} \cdot Q, 2)$$
     - Seller's gold is incremented: $\text{agent.gold} \leftarrow \text{agent.gold} + \text{revenue}$.
     - Seller's inventory is decremented: $\text{agent.inventory}[item] \leftarrow \text{agent.inventory}[item] - Q$.
     - Market supply is incremented: $\text{market.supply}[item] \leftarrow \text{market.supply}[item] + Q$.
     - Transaction record logs: $\text{unit\_price} = P_{\text{unit}}$, $\text{tax\_paid} = 0.0$, $\text{total\_cost} = \text{revenue}$.

3. **Tax Rates & Edge Cases**:
   - If $r_{\text{tax}} = 0.0$: $T = 0.0$, $\text{total\_cost} = P_{\text{unit}} \cdot Q$.
   - If $r_{\text{tax}} = 0.80$: $T = 0.80 \cdot P_{\text{unit}} \cdot Q$, total cost is $1.80 \times \text{subtotal}$.
   - Float precision protection: `calculate_tax` guards against $Q \le 0$, $P_{\text{unit}} \le 0$, or $r_{\text{tax}} \le 0$, returning $0.0$.

### 2.3 Transaction Validation Predicate Matrix

The validation function `validate_transaction(agent, item, action, quantity, tax_rate)` evaluates preconditions before any mutation occurs:

| Action | Precondition | Mathematical / Logical Check | Failure Response |
| :--- | :--- | :--- | :--- |
| `HOLD` / `CRAFT` | None | Always `True` | N/A (valid no-op) |
| `BUY` | Valid Item | `item is not None` and `item.name in state.items` | `(False, "Item must be specified for BUY.")` |
| `BUY` | Positive Quantity | $Q \ge 1$ | `(False, "Invalid quantity...")` |
| `BUY` | Market Supply Availability | $\text{item.supply} \ge Q$ | `(False, "Insufficient market supply: required Q, available S")` |
| `BUY` | Solvency (Gold Balance) | $\text{round}(\text{agent.gold}, 2) + 10^{-7} \ge Q \cdot P + T$ | `(False, "Insufficient gold: required C, available G")` |
| `SELL` | Valid Item | `item is not None` and `item.name in state.items` | `(False, "Item must be specified for SELL.")` |
| `SELL` | Positive Quantity | $Q \ge 1$ | `(False, "Invalid quantity...")` |
| `SELL` | Inventory Availability | $\text{agent.inventory.get}(item, 0) \ge Q$ | `(False, "Insufficient inventory: agent has N, required Q")` |

### 2.4 Atomic Trade Execution Lifecycle

Each transaction undergoes deterministic atomic processing:

```
[Agent Decision Received]
          │
          ▼
Is agent registered in state.agents?
    ├─ No  ──► Emit REJECTED TransactionRecord (reason: agent not found)
    └─ Yes ──► Update agent.last_action = decision
                 │
                 ▼
Is action HOLD or CRAFT?
    ├─ Yes ──► Emit EXECUTED TransactionRecord (total_cost=0, tax=0), no state change
    └─ No (BUY or SELL)
                 │
                 ▼
Is item present in state.items?
    ├─ No  ──► Emit REJECTED TransactionRecord (reason: item catalog missing)
    └─ Yes
         │
         ▼
Run validate_transaction(agent, item, action, quantity, tax_rate)
    ├─ Invalid ──► Emit REJECTED TransactionRecord (reason from validator)
    │             NO GOLD DEDUCTED, NO INVENTORY TOUCHED, NO SUPPLY MUTATED
    └─ Valid
         │
         ▼
Atomic Commit:
  [If BUY]:
    agent.gold -= total_cost
    agent.inventory[item] += quantity
    item.supply -= quantity
    Emit EXECUTED TransactionRecord
  [If SELL]:
    agent.gold += revenue
    agent.inventory[item] -= quantity
    item.supply += quantity
    Emit EXECUTED TransactionRecord
         │
         ▼
Append TransactionRecord to state.recent_transactions
```

### 2.5 Macroeconomic Shock Mutators

1. **`apply_dragon_attack(state: EconomyState) -> None`**:
   - Target commodity: `"Health Potion"`.
   - Mutates `state.items["Health Potion"].supply = 2`.
   - Mutates `state.items["Health Potion"].price = 35.0`.
   - Idempotent and deterministic: whether existing supply is 100 or 0, it becomes exactly 2; whether existing price is 20.0 or 50.0, it becomes exactly 35.0.
   - Other items ("Iron Sword", "Raw Gem") are untouched.

2. **`apply_gold_rush(state: EconomyState, gold_amount: float = 100.0) -> None`**:
   - Iterates through all active agents: `for agent in state.agents.values()`.
   - Directly credits `agent.gold = round(agent.gold + gold_amount, 2)`.
   - Protects against float drift via explicit 2-decimal rounding.
   - Preserves agent inventories and market supplies.

### 2.6 Decoupling Tick Price Adjustment from In-Tick Trades

In an asynchronous multi-agent simulation where 3 autonomous agents decide concurrently via `asyncio.gather()`:
- **During the tick**: Agents execute trades at the tick's published market prices. This prevents arbitrary race conditions where the coroutine resolution order alters the unit price paid by different agents.
- **At the end of the tick**: `update_market_prices(state, tick_transactions, k)` calculates net demand $\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$ strictly from `EXECUTED` transactions. Any `REJECTED` or `SKIPPED` transaction is filtered out so failed attempts do not skew market prices.

---

## 3. Caveats

1. **Tax Incidence (Buyer vs Seller)**:
   - In economic modeling, taxes can be levied on buyer, seller, or shared. `PROJECT.md` line 45 specifically dictates: `"Buyer Gold Validation: Prevents purchases when agent gold < Q * P_unit * (1 + r_tax)"`, and `ORIGINAL_REQUEST.md` line 46 specifies: `"Seller Inventory Validation: Prevents sales when agent inventory < Q"`.
   - Therefore, tax $T$ is applied as a consumption/sales tax paid by the buyer. Sellers receive gross proceeds $Q \cdot P_{\text{unit}}$ with `tax_paid = 0.0`. If a dual-sided transaction fee is ever required in future phases, the tax function is decoupled and can be applied symmetrically without restructuring the engine.
2. **CRAFT Action in Phase 1**:
   - `ActionType.CRAFT` exists in the schema to support Phase 2 crafting mechanics. For Phase 1, `CRAFT` is treated as a valid no-op equivalent to `HOLD` per `PROJECT.md` line 93 (`# fallback to HOLD in Phase 1`).
3. **Floating Point Rounding Strategy**:
   - Standard Python floating point operations can accumulate representation errors (e.g. `100.0 - 22.0 - 4.4 = 73.60000000000001`).
   - All balance updates, costs, and taxes in `src/market.py` must explicitly apply `round(value, 2)` at every step.
   - When checking solvency in `validate_transaction`, an epsilon tolerance $+10^{-7}$ ensures that minor representation artifacts (e.g., `21.999999999999996` for an agent with 22 Gold) do not falsely reject legitimate trades.
4. **Market Supply Underflow Prevention**:
   - If market supply is less than the requested buy quantity (e.g., supply is 2, but agent requests 5), `validate_transaction` rejects the transaction in full rather than partial-filling. This preserves atomic transaction semantics and simplifies tick auditability.

---

## 4. Conclusion

The specification for `src/market.py` is complete, mathematically bounded, and ready for clean implementation by `m1_worker`.

### 4.1 Interface Contract Specification

```python
"""Interface contract for src/market.py"""

from typing import Dict, List, Optional, Tuple
from src.models import (
    ActionType,
    AgentDecision,
    AgentState,
    EconomyState,
    ItemState,
    TransactionRecord,
)

def calculate_new_price(
    old_price: float,
    net_demand: int,
    k: float = 0.05,
    min_price: float = 1.0,
) -> float:
    """Computes P_new = max(min_price, round(old_price * (1 + k * net_demand), 2))."""
    ...

def calculate_tax(
    unit_price: float,
    quantity: int,
    tax_rate: float,
) -> float:
    """Computes T = round(unit_price * quantity * tax_rate, 2)."""
    ...

def validate_transaction(
    agent: AgentState,
    item: Optional[ItemState],
    action: ActionType,
    quantity: int,
    tax_rate: float,
) -> Tuple[bool, str]:
    """Validates buyer gold or seller inventory constraints."""
    ...

def execute_transaction(
    state: EconomyState,
    agent_name: str,
    decision: AgentDecision,
) -> TransactionRecord:
    """Executes validated transaction atomically against EconomyState."""
    ...

def calculate_net_demand(
    transactions: List[TransactionRecord],
    item_name: str,
) -> int:
    """Computes net demand ΔD = Q_bought - Q_sold for an item across EXECUTED transactions."""
    ...

def update_market_prices(
    state: EconomyState,
    tick_transactions: List[TransactionRecord],
    k: float = 0.05,
    min_price: float = 1.0,
) -> Dict[str, float]:
    """Aggregates executed transactions in a tick and updates market prices."""
    ...

def apply_dragon_attack(state: EconomyState) -> None:
    """Sets Health Potion supply = 2 and base price = 35.0."""
    ...

def apply_gold_rush(state: EconomyState, gold_amount: float = 100.0) -> None:
    """Credits gold_amount to all agents."""
    ...
```

### 4.2 Reference Implementation Artifact
A production-ready reference implementation adhering to this exact contract has been authored and placed at:
`c:\Users\Aditya S Yadav\Desktop\anything-to-website\my-game-economy-simulator\.agents\teamwork\m1_explorer_2\proposed_market.py`

The implementing worker (`m1_worker`) can copy or reference `proposed_market.py` directly into `src/market.py` upon milestone execution.

---

## 5. Verification Method

To independently verify the market math, validation logic, and state mutations:

### 5.1 Deterministic Test Cases for `tests/test_market.py`

1. **Price Discovery Math Tests**:
   - Zero net demand: `calculate_new_price(20.0, 0, 0.05, 1.0) == 20.0`
   - Positive demand: `calculate_new_price(20.0, 3, 0.05, 1.0) == 23.0`
   - Negative demand: `calculate_new_price(20.0, -4, 0.05, 1.0) == 16.0`
   - Extreme negative demand (Floor test): `calculate_new_price(20.0, -25, 0.05, 1.0) == 1.0`
   - Pre-existing floor test: `calculate_new_price(1.0, -10, 0.05, 1.0) == 1.0`
   - Rounding check: `calculate_new_price(15.55, 1, 0.05, 1.0) == round(15.55 * 1.05, 2) == 16.33`

2. **Tax Calculation Tests**:
   - Zero tax rate: `calculate_tax(20.0, 2, 0.0) == 0.0`
   - Standard tax rate (10%): `calculate_tax(20.0, 2, 0.10) == 4.0`
   - High tax rate (50%): `calculate_tax(30.0, 1, 0.50) == 15.0`
   - Maximum tax rate (80%): `calculate_tax(35.0, 2, 0.80) == 56.0`
   - Fractional rounding: `calculate_tax(19.99, 3, 0.07) == round(19.99 * 3 * 0.07, 2) == 4.20`

3. **Transaction Validation Tests**:
   - Valid BUY with exact gold: agent has 22.0 Gold, item price 20.0, quantity 1, tax rate 0.10 (total 22.0) $\to$ `True`
   - Invalid BUY with deficient gold: agent has 21.90 Gold, item price 20.0, quantity 1, tax rate 0.10 (total 22.0) $\to$ `False`
   - Invalid BUY with insufficient market supply: item supply = 1, requested 2 $\to$ `False`
   - Valid SELL with exact inventory: agent has 2 Potions, requested 2 $\to$ `True`
   - Invalid SELL with deficient inventory: agent has 1 Potion, requested 2 $\to$ `False`
   - Always valid HOLD: `True` with no mutation

4. **Atomic Execution Tests**:
   - Execute successful BUY: agent gold drops from 100.0 to 78.0, inventory increments by 1, market supply decrements by 1, status is `EXECUTED`.
   - Execute rejected BUY: agent has 10.0 Gold, total cost 22.0 $\to$ status is `REJECTED`, agent gold stays 10.0, inventory unchanged, market supply unchanged.
   - Execute successful SELL: agent gold rises from 50.0 to 70.0, inventory decrements by 1, market supply increments by 1, status is `EXECUTED`.

5. **Shock Event Tests**:
   - `apply_dragon_attack(state)`: verify `state.items["Health Potion"].supply == 2` and `state.items["Health Potion"].price == 35.0`.
   - `apply_gold_rush(state, 100.0)`: verify every agent in `state.agents` has `gold` incremented by exactly `100.0`.

### 5.2 Verification Commands

Run the test suite via PowerShell from project root:
```powershell
python -m pytest tests/test_market.py -v
```
Full test run:
```powershell
pytest tests/ -v
```

### 5.3 Invalidation Conditions
- If the pricing discovery formula in `PROJECT.md` or `ORIGINAL_REQUEST.md` is modified to include non-linear demand or different sensitivity factors without updating this design.
- If policy constraints redefine tax calculation to be seller-side or split 50/50 without updating settlement accounting.
