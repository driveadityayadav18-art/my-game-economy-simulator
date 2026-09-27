# Project: AI-Driven Game Economy Simulator (Phase 1)

## Architecture
The system is an asynchronous simulation engine built with Python 3.11+, FastAPI, Pydantic, and Uvicorn. It models an autonomous game economy where 3 persona agents trade 3 goods under mathematical supply/demand price discovery with policy controls.

```
                      ┌──────────────────────────────────────────────┐
                      │              FastAPI REST & WS               │
                      │  GET /state, POST /simulation/*,             │
                      │  POST /policy/tax, POST /policy/event, /ws   │
                      └──────────────────────┬───────────────────────┘
                                             │
                      ┌──────────────────────▼───────────────────────┐
                      │          Simulation Engine Store             │
                      │        (In-Memory State Coordinator)         │
                      └──────────────┬──────────────────────┬────────┘
                                     │                      │
       ┌─────────────────────────────▼────┐    ┌────────────▼────────────────────────┐
       │   Market & Price Discovery Math  │    │     Autonomous Multi-Provider       │
       │ P_new = max(1.0, P*(1 + k*ΔD))   │    │          LLM Agent Module           │
       │ T = P * r_tax, Trade Validation  │    │ Garrick / Cora / Boran              │
       │ "Dragon Attack" & "Gold Rush"    │    │ Async gather + Heuristic Fallback   │
       └──────────────────────────────────┘    └─────────────────────────────────────┘
```

### Module Boundaries & Responsibilities:
1. `src/config.py`: Environment configuration, API keys, default economic parameters ($k=0.05$, price floor $1.0$, tick interval $4.0$s, tax limits $0.0-0.80$, timeout $2.0$s).
2. `src/models.py`: Pydantic data schemas: `AgentDecision`, `ItemState`, `AgentState`, `EconomyState`, `TransactionRecord`, `PolicyTaxRequest`, `PolicyEventRequest`, `SimulationStatus`.
3. `src/market.py`: Pure mathematical pricing functions, transaction taxes, gold & inventory constraints validation, atomic trade execution, economic shock mutators.
4. `src/agents.py`: Persona prompt builders, multi-provider LLM adapter (OpenAI, Anthropic, Gemini), strict JSON parser, simulated heuristic fallback runner, and parallel executor via `asyncio.gather()`.
5. `src/simulation.py`: In-memory economy state manager, asynchronous tick loop runner, trade aggregation, single-tick stepper, and state broadcaster.
6. `src/main.py`: FastAPI application hosting REST endpoints (`GET /state`, `POST /simulation/tick`, `POST /simulation/start`, `POST /simulation/stop`, `POST /policy/tax`, `POST /policy/event`, `/ws`).

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Net Demand Calculation | Computes net demand $\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$ across valid tick transactions | M1 | survey 1 |
| 2 | Algorithmic Price Discovery | Adjusts item prices via $P_{\text{new}} = \max(1.0, P_{\text{old}} \cdot (1 + k \cdot \Delta D))$ ($k=0.05$) | M1 | survey 1 |
| 3 | Minimum Price Floor Enforcement | Guarantees price never drops below 1.0 Gold under heavy sell pressure | M1 | survey 1 |
| 4 | Supported Item Catalog | Strictly manages "Health Potion", "Iron Sword", "Raw Gem" | M1 | survey 1 |
| 5 | Market Inventory Tracking | Tracks available market supplies and enforces finite stock constraints | M1 | survey 1 |
| 6 | Transaction Tax Calculation | Calculates transaction tax $T = P_{\text{unit}} \cdot r_{\text{tax}}$ ($0.0 \le r_{\text{tax}} \le 0.80$) | M1 | survey 1 |
| 7 | Buyer Gold Validation | Prevents purchases when agent gold $< Q \cdot P_{\text{unit}} \cdot (1 + r_{\text{tax}})$ | M1 | survey 1 |
| 8 | Seller Inventory Validation | Prevents sales when agent inventory $< Q$ | M1 | survey 1 |
| 9 | Atomic State Finalization | Commits balances, inventory, and logs only when all validation checks pass | M1 | survey 1 |
| 10 | Persona: Garrick the Greedy | Hoards gold/rare items, buys low, sells high aggressively | M2 | survey 2 |
| 11 | Persona: Cora the Farmer | Prioritizes steady income, sells raw gems consistently, avoids debt | M2 | survey 2 |
| 12 | Persona: Boran the Adventurer | High consumption, spends gold on potions/weapons, low balance | M2 | survey 2 |
| 13 | Multi-Provider LLM Engine | Adapters for OpenAI, Anthropic, Gemini via `.env` configuration | M2 | survey 2 |
| 14 | Structured JSON Schema Enforcement | Enforces Draft-07 schema (`action`, `item`, `quantity`, `reasoning`) | M2 | survey 2 |
| 15 | Parallel Agent Concurrency | Executes all 3 agent decisions simultaneously via `asyncio.gather()` in $<2.0$s | M2 | survey 2 |
| 16 | Simulated Heuristic Fallback | Safe fallback to valid "HOLD" on missing keys, network failure, or timeout $>2.0$s | M2 | survey 2 |
| 17 | In-Memory State Store | Thread/async safe store holding tick, prices, agents, taxes, history | M3 | survey 1, 2 |
| 18 | Manual Single-Tick Stepping | `POST /simulation/tick` deterministically advances simulation by 1 tick | M3 | survey 2 |
| 19 | Background Loop Execution | `POST /simulation/start` & `POST /simulation/stop` manage 4s async loop | M3 | survey 2 |
| 20 | State Inspection Endpoint | `GET /state` returns complete snapshot of economy | M3 | survey 2 |
| 21 | Tax Policy API | `POST /policy/tax` updates tax rate clamped to $[0.0, 0.80]$ | M3 | survey 1, 2 |
| 22 | Shock: Dragon Attack | `POST /policy/event` sets Health Potion supply = 2, base price = 35.0 Gold | M3 | survey 1, 2 |
| 23 | Shock: Gold Rush | `POST /policy/event` credits $+100$ Gold immediately to all active agents | M3 | survey 1, 2 |
| 24 | Real-Time State Streaming | `/ws` WebSocket endpoint broadcasting snapshot JSON on tick completion | M3 | survey 1, 2 |
| 25 | E2E Test Suite (Tiers 1-4) | Systematic requirement-driven opaque-box test suite | Test Track | survey 1, 2, 3 |
| 26 | Final Integration & E2E 100% Pass | All E2E tests pass cleanly with pytest | M4 | original request |
| 27 | Adversarial Hardening (Tier 5) | White-box stress-testing, boundary tests, and edge case audits | M5 | original request |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| Test Track | E2E Testing Suite | Test infra, fixtures, and 4 tiers of opaque-box tests (Tiers 1-4), publishing `TEST_READY.md` | none | PLANNED |
| M1 | Deterministic Market & State Store | `config.py`, `models.py`, `market.py` — pricing formulas, tax math, inventory & gold validation, shocks | none | PLANNED |
| M2 | Parallel Multi-Provider LLM Agent Module | `agents.py` — 3 personas, multi-provider adapter, JSON schema parsing, simulated heuristic fallback, `asyncio.gather()` | M1 | PLANNED |
| M3 | Simulation Tick Loop & Policy REST API | `simulation.py`, `main.py` — state store, async tick loop, REST endpoints (`/state`, `/simulation/*`, `/policy/*`, `/ws`) | M1, M2 | PLANNED |
| M4 | Final Integration & E2E Pass | Run full pytest suite from Test Track; verify 100% passing tests and resolve any discrepancies | M3, Test Track | PLANNED |
| M5 | Adversarial Hardening (Tier 5) | Inverted challenger loop for white-box edge case hardening and coverage guarantees | M4 | PLANNED |

---

## Interface Contracts

### `src/models.py`
```python
from enum import Enum
from typing import Optional, Literal, Dict, List
from pydantic import BaseModel, Field

class ActionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CRAFT = "CRAFT"  # fallback to HOLD in Phase 1

ItemName = Literal["Health Potion", "Iron Sword", "Raw Gem"]

class AgentDecision(BaseModel):
    action: ActionType
    item: Optional[ItemName] = None
    quantity: int = Field(default=1, ge=1, le=10)
    reasoning: str = Field(..., max_length=120)

class ItemState(BaseModel):
    name: str
    price: float = Field(..., ge=1.0)
    supply: int = Field(default=100, ge=0)

class AgentState(BaseModel):
    name: str
    persona: str
    gold: float = Field(..., ge=0.0)
    inventory: Dict[str, int]
    last_action: Optional[AgentDecision] = None

class TransactionRecord(BaseModel):
    tick: int
    agent_name: str
    action: ActionType
    item: Optional[str]
    quantity: int
    unit_price: float
    tax_paid: float
    total_cost: float
    status: Literal["EXECUTED", "REJECTED", "SKIPPED"]
    reason: Optional[str] = None

class EconomyState(BaseModel):
    tick: int = 0
    running: bool = False
    tax_rate: float = Field(default=0.10, ge=0.0, le=0.80)
    items: Dict[str, ItemState]
    agents: Dict[str, AgentState]
    recent_transactions: List[TransactionRecord] = []
```

### `src/market.py`
```python
def calculate_new_price(old_price: float, net_demand: int, k: float = 0.05, min_price: float = 1.0) -> float:
    """Computes P_new = max(min_price, old_price * (1 + k * net_demand)). Rounded to 2 decimals."""
    ...

def calculate_tax(unit_price: float, quantity: int, tax_rate: float) -> float:
    """Computes T = unit_price * quantity * tax_rate. Rounded to 2 decimals."""
    ...

def validate_transaction(agent: AgentState, item: ItemState, action: ActionType, quantity: int, tax_rate: float) -> tuple[bool, str]:
    """Validates buyer gold or seller inventory constraints."""
    ...

def execute_transaction(state: EconomyState, agent_name: str, decision: AgentDecision) -> TransactionRecord:
    """Executes validated transaction atomically against EconomyState."""
    ...

def apply_dragon_attack(state: EconomyState) -> None:
    """Sets Health Potion supply = 2 and base price = 35.0."""
    ...

def apply_gold_rush(state: EconomyState, gold_amount: float = 100.0) -> None:
    """Credits gold_amount to all agents."""
    ...
```

### `src/agents.py`
```python
class BaseAgent:
    name: str
    persona: str
    
    async def decide(self, state_snapshot: dict) -> AgentDecision:
        """Evaluates decision within 2.0s; falls back to HOLD on error or timeout."""
        ...
```

---

## Code Layout
```
my-game-economy-simulator/
├── .agents/                      # Multi-agent coordination metadata
├── specs/                        # Project specifications & constitution
├── src/                          # Implementation Track write ownership
│   ├── __init__.py
│   ├── config.py                 # Settings & env vars
│   ├── models.py                 # Pydantic schemas & state structures
│   ├── market.py                 # Pricing math & trade validation
│   ├── agents.py                 # 3 personas, multi-provider adapter & fallback
│   ├── simulation.py             # Tick loop & in-memory coordinator
│   └── main.py                   # FastAPI REST app & endpoints
├── tests/                        # E2E Testing Track write ownership
│   ├── __init__.py
│   ├── conftest.py               # Shared test fixtures & TestClient
│   ├── test_tier1_features.py    # Tier 1: Feature isolation tests (>=5 per feature)
│   ├── test_tier2_boundaries.py  # Tier 2: Boundary & corner tests (>=5 per feature)
│   ├── test_tier3_pairwise.py    # Tier 3: Cross-feature combinations
│   └── test_tier4_scenarios.py   # Tier 4: Real-world application scenarios
├── requirements.txt              # Standard dependencies
├── .env.example                  # Environment configuration template
└── PROJECT.md                    # Living master index
```
