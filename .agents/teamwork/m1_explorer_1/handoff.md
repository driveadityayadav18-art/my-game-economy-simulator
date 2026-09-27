# Milestone 1 Exploration & Specification Report: Config & Models (`src/config.py` & `src/models.py`)

**Explorer**: `teamwork_preview_explorer` (M1 Explorer 1)  
**Target Files**: `src/config.py`, `src/models.py`  
**Reference Code Artifacts**: 
- `.agents/teamwork/m1_explorer_1/proposed_config.py`
- `.agents/teamwork/m1_explorer_1/proposed_models.py`  
**Date**: 2026-09-27  

---

## 1. Observation

Direct observations and citations from authoritative repository sources:

### 1.1 Requirements & Knobs (`ORIGINAL_REQUEST.md`)
1. **Macroeconomic Knobs & Formula Constants**:
   - `ORIGINAL_REQUEST.md:21`: "$P_{\\text{new}} = \\max(1.0, P_{\\text{old}} \\cdot (1 + k \\cdot \\Delta D))$ with default sensitivity $k = 0.05$ and minimum price floor of $1.0$ Gold."
   - `ORIGINAL_REQUEST.md:23`: "Calculate transaction taxes $T = P_{\\text{unit}} \\cdot r_{\\text{tax}}$ and validate agent gold/inventory constraints before finalizing transactions."
   - `ORIGINAL_REQUEST.md:35`: "asynchronous tick loop (~4 second interval)".
   - `ORIGINAL_REQUEST.md:32, 48, 60, 69`: Agent timeout cutoff strictly set to $2.0$s; execution exceeding $2.0$s must fall back to `"HOLD"`.
   - `ORIGINAL_REQUEST.md:39`: "Updates the tax rate $r_{\\text{tax}}$ (clamped between 0% and 80%)."
2. **Item Catalog & Personas**:
   - `ORIGINAL_REQUEST.md:22`: Traded items strictly cataloged as `"Health Potion"`, `"Iron Sword"`, `"Raw Gem"`.
   - `ORIGINAL_REQUEST.md:27-29`: Personas:
     - Garrick the Greedy: Hoards rare items and gold; buys low, sells high aggressively.
     - Cora the Farmer: Prioritizes steady income; sells raw materials consistently, avoids debt/risk.
     - Boran the Adventurer: Prioritizes immediate consumption; spends gold on potions/weapons, maintains low balance.
   - Dispatch instruction: Starting gold balances: Garrick ($150.0$), Cora ($60.0$), Boran ($40.0$). Default item prices: Health Potion ($20.0$, supply $100$), Iron Sword ($30.0$, supply $100$), Raw Gem ($15.0$, supply $100$).

### 1.2 Master Contract & Code Layout (`PROJECT.md`)
1. `PROJECT.md:83-134` defines the exact interface contracts:
   - `ActionType(str, Enum)`: `BUY`, `SELL`, `HOLD`, `CRAFT`.
   - `ItemName = Literal["Health Potion", "Iron Sword", "Raw Gem"]`.
   - `AgentDecision`: `action: ActionType`, `item: Optional[ItemName] = None`, `quantity: int = Field(default=1, ge=1, le=10)`, `reasoning: str = Field(..., max_length=120)`.
   - `ItemState`: `name: str`, `price: float = Field(..., ge=1.0)`, `supply: int = Field(default=100, ge=0)`.
   - `AgentState`: `name: str`, `persona: str`, `gold: float = Field(..., ge=0.0)`, `inventory: Dict[str, int]`, `last_action: Optional[AgentDecision] = None`.
   - `TransactionRecord`: `tick: int`, `agent_name: str`, `action: ActionType`, `item: Optional[str]`, `quantity: int`, `unit_price: float`, `tax_paid: float`, `total_cost: float`, `status: Literal["EXECUTED", "REJECTED", "SKIPPED"]`, `reason: Optional[str] = None`.
   - `EconomyState`: `tick: int = 0`, `running: bool = False`, `tax_rate: float = Field(default=0.10, ge=0.0, le=0.80)`, `items: Dict[str, ItemState]`, `agents: Dict[str, AgentState]`, `recent_transactions: List[TransactionRecord] = []`.
   - `PolicyTaxRequest`, `PolicyEventRequest`, `SimulationStatus`.

### 1.3 Agent Decision Draft-07 JSON Schema (`specs/features/feature_specification_mvp_engine_dashboard (1).md`)
Lines 40-52 specify the required Draft-07 JSON schema for structured LLM reasoning:
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

### 1.4 Dependency Environment Audit (`requirements.txt`)
`requirements.txt` specifies:
```
fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
python-dotenv>=1.0.0
websockets>=12.0
openai>=1.14.0
anthropic>=0.18.0
google-generativeai>=0.4.0
```
**CRITICAL FINDING**: `pydantic-settings` is **NOT** included in `requirements.txt`. In Pydantic v2 (`pydantic>=2.6.0`), importing `BaseSettings` directly from `pydantic` raises `PydanticImportError: 'BaseSettings' has been moved to the 'pydantic-settings' package`. Therefore, `src/config.py` MUST NOT unconditionally import `from pydantic_settings import BaseSettings` or `from pydantic import BaseSettings`. It must use `pydantic.BaseModel` with `python-dotenv` / `os.getenv` or a safe conditional fallback.

### 1.5 Test Suite Expectations (`tests/conftest.py`, `tests/test_tier1_features.py`, `tests/test_tier2_boundaries.py`)
1. **Model Methods**:
   - Tests invoke `fresh_economy_state.model_dump()` (`tests/test_tier1_features.py:401`).
   - Tests invoke `AgentDecision.model_validate(...)` (`tests/test_tier1_features.py:413`).
   - Tests invoke `EconomyState.model_validate(...)` (`tests/test_tier1_features.py:562, 595`).
2. **Strict Validation Boundaries**:
   - `quantity < 1` and `quantity > 10` MUST raise `pydantic.ValidationError` (`test_boundary_quantity_zero_rejected`, `test_boundary_quantity_eleven_rejected` in `test_tier2_boundaries.py:363, 375`).
   - `len(reasoning) > 120` MUST raise `pydantic.ValidationError` when constructing `AgentDecision` (`test_boundary_reasoning_length_one_hundred_twenty_one_rejected` in `test_tier2_boundaries.py:399`).
   - `action` not in `ActionType` enum values MUST raise `ValidationError` (`test_json_schema_invalid_action_rejected` in `test_tier1_features.py:437`).
3. **Policy Shock Payloads**:
   - `tests/test_tier1_features.py:682-684` tests `test_client.post("/policy/event", json={"event": "Dragon Attack"})` with fallback to `json={"event_type": "Dragon Attack"}`.
   - `tests/test_tier1_features.py:724-726` tests `test_client.post("/policy/event", json={"event": "Gold Rush"})` with fallback to `json={"event_type": "Gold Rush"}`.
   - `PolicyEventRequest` must accept either `event` or `event_type`.
4. **Policy Tax Payloads**:
   - `tests/test_tier1_features.py:638, 646` tests boundary tax rates `-0.10` and `0.95`, expecting status codes in `[400, 422, 200]` and resulting state tax rate clamped within $[0.0, 0.80]$.

---

## 2. Logic Chain

From the observed evidence, the structural design choices follow a rigorous deduction chain:

1. **Dependency Resilience for `src/config.py`**:
   - *Premise*: `requirements.txt` specifies `pydantic>=2.6.0` and `python-dotenv>=1.0.0`, but omits `pydantic-settings`.
   - *Deduction*: Writing `from pydantic_settings import BaseSettings` without safety checks will crash with `ModuleNotFoundError` in environments installing strictly from `requirements.txt`.
   - *Design Decision*: Implement `Settings(BaseModel)` using field-level `default_factory=lambda: float(os.getenv(...))` initialized after calling `dotenv.load_dotenv()`. This provides 100% standard library + Pydantic v2 native compatibility, allows environment overrides via `.env` or system variables, allows programmatic overrides via `Settings(SIMULATION_TICK_INTERVAL=2.0)` in unit tests, and avoids external package dependencies.

2. **Circular Dependency Prevention**:
   - *Premise*: `config.py` needs to provide default items (`get_default_items()`), default agents (`get_default_agents()`), and default starting state (`get_default_economy_state()`), which construct instances of `ItemState`, `AgentState`, and `EconomyState` defined in `models.py`. In turn, `models.py` references validation bounds.
   - *Deduction*: A top-level `from src.models import ItemState` inside `config.py` while `models.py` imports `config.py` would create an import cycle.
   - *Design Decision*: Keep raw configuration constants in `DEFAULT_ITEMS_CONFIG` and `DEFAULT_AGENTS_CONFIG` as pure Python dictionaries in `config.py`. Expose factory functions `get_default_items()`, `get_default_agents()`, and `get_default_economy_state()` that perform local lazy imports of the Pydantic models. This completely prevents circular dependencies.

3. **Strict Validation vs. Agent Truncation**:
   - *Premise*: `test_boundary_reasoning_length_one_hundred_twenty_one_rejected` in `test_tier2_boundaries.py:399` expects direct construction `AgentDecision(..., reasoning="X" * 121)` to raise `pydantic.ValidationError`. At the same time, spec survey notes that the agent parsing layer should gracefully handle long LLM responses.
   - *Deduction*: `AgentDecision` in `models.py` must enforce strict `max_length=120` without silent truncation in the model constructor so that boundary tests pass as written.
   - *Design Decision*: Place `max_length=120` on the `reasoning` field in `AgentDecision`. Auto-truncation or fallback to `"HOLD"` must be executed by the agent parsing adapter in `src/agents.py`, preserving the contract integrity of the data model.

4. **Draft-07 Schema Compliance**:
   - *Premise*: `feature_specification_mvp_engine_dashboard (1).md:40-52` defines the exact Draft-07 schema for LLM generation. Pydantic v2's default `model_json_schema()` produces JSON Schema draft 2020-12 and formats nullable fields with `anyOf` rather than Draft-07 `"type": ["string", "null"]`.
   - *Deduction*: Relying solely on default Pydantic schema generation may cause incompatibilities with older LLM structured output validators expecting Draft-07.
   - *Design Decision*: Define `AGENT_DECISION_DRAFT07_SCHEMA` explicitly as a module constant in `models.py` matching the specification line-for-line, and attach it to `AgentDecision.model_config["json_schema_extra"]`.

5. **Payload Flexibility for Policy Endpoints**:
   - *Premise*: `tests/test_tier1_features.py:683-684` executes:
     `res = test_client.post("/policy/event", json={"event": "Dragon Attack"})`
     `if res.status_code == 422: res = test_client.post("/policy/event", json={"event_type": "Dragon Attack"})`
   - *Deduction*: Client calls may send either `event` or `event_type`.
   - *Design Decision*: `PolicyEventRequest` declares both `event: Optional[str] = None` and `event_type: Optional[str] = None`, with a `@model_validator(mode="after")` that synchronizes both fields, guaranteeing immediate 200 OK regardless of which key the client provides.
   - *Premise*: `tests/test_tier1_features.py:639, 647` accepts status `[400, 422, 200]` for tax rates outside $[0.0, 0.80]$.
   - *Design Decision*: `PolicyTaxRequest` accepts `tax_rate: float` and exposes a `.clamped_rate() -> float` helper method returning `max(0.0, min(0.80, round(self.tax_rate, 4)))`.

---

## 3. Caveats

1. **Crafting Mechanics**:
   - `ActionType` includes `CRAFT` per `PROJECT.md:93` and Draft-07 schema enum, but no crafting recipes exist in Phase 1 MVP. Per `PROJECT.md:93`, `CRAFT` falls back to `HOLD`.
2. **Pydantic Serialization**:
   - In Pydantic v2, `.model_dump()` is standard, while `.dict()` is deprecated but available. `tests/conftest.py` and `tests/test_tier1_features.py` use `.model_dump()` and `.model_validate()`. Both reference files in this report are fully tested against Pydantic v2 conventions.
3. **Floating Point Rounding**:
   - Python IEEE 754 float arithmetic can cause micro-drift (e.g. $10.0 \cdot 1.05 = 10.500000000000002$). Field validators on `price`, `gold`, and `unit_price`/`tax_paid`/`total_cost` automatically round values to 2 decimal places to guarantee invariant `round(val, 2) == val`.

---

## 4. Conclusion

The architectural blueprints for `src/config.py` and `src/models.py` are complete, robust, and validated against all 4 tiers of project specifications and tests:

### 4.1 Specification Blueprint: `src/config.py`
Located at `.agents/teamwork/m1_explorer_1/proposed_config.py`:
- **Settings Class**:
  - `SIMULATION_TICK_INTERVAL`: float = 4.0s (env: `SIMULATION_TICK_INTERVAL`)
  - `LLM_TIMEOUT_SECONDS`: float = 2.0s (env: `LLM_TIMEOUT_SECONDS`)
  - `DEFAULT_TAX_RATE`: float = 0.10 (env: `DEFAULT_TAX_RATE`)
  - `MIN_TAX_RATE`: float = 0.0 (env: `MIN_TAX_RATE`)
  - `MAX_TAX_RATE`: float = 0.80 (env: `MAX_TAX_RATE`)
  - `PRICE_SENSITIVITY_K`: float = 0.05 (env: `PRICE_SENSITIVITY_K`)
  - `PRICE_FLOOR`: float = 1.0 (env: `PRICE_FLOOR`)
  - LLM credentials: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `LLM_PROVIDER="simulated"`, `DEFAULT_LLM_MODEL="gpt-4o-mini"`
  - Server: `HOST="0.0.0.0"`, `PORT=8000`
- **Catalog & Personas**:
  - `DEFAULT_ITEMS_CONFIG`: "Health Potion" (20.0, 100), "Iron Sword" (30.0, 100), "Raw Gem" (15.0, 100).
  - `DEFAULT_AGENTS_CONFIG`: Garrick (150 gold), Cora (60 gold), Boran (40 gold).
- **Zero-Dependency Lazy Factories**:
  - `get_default_items() -> Dict[str, ItemState]`
  - `get_default_agents() -> Dict[str, AgentState]`
  - `get_default_economy_state() -> EconomyState`

### 4.2 Specification Blueprint: `src/models.py`
Located at `.agents/teamwork/m1_explorer_1/proposed_models.py`:
- **Enums & Types**:
  - `ActionType(str, Enum)`: `BUY`, `SELL`, `HOLD`, `CRAFT`.
  - `ItemName = Literal["Health Potion", "Iron Sword", "Raw Gem"]`.
  - `VALID_ITEMS = ("Health Potion", "Iron Sword", "Raw Gem")`.
  - `AGENT_DECISION_DRAFT07_SCHEMA`: Exact Draft-07 schema object.
- **Models**:
  - `AgentDecision`: `action`, `item`, `quantity` ($1..10$), `reasoning` ($\le 120$).
  - `ItemState`: `name`, `price` ($\ge 1.0$, rounded to 2 decimals), `supply` ($\ge 0$).
  - `AgentState`: `name`, `persona`, `gold` ($\ge 0.0$, rounded to 2 decimals), `inventory` (all counts $\ge 0$), `last_action`.
  - `TransactionRecord`: `tick`, `agent_name`, `action`, `item`, `quantity`, `unit_price`, `tax_paid`, `total_cost`, `status` (`"EXECUTED"`, `"REJECTED"`, `"SKIPPED"`), `reason`.
  - `EconomyState`: `tick`, `running`, `tax_rate` ($[0.0, 0.80]$), `items`, `agents`, `recent_transactions`.
  - `PolicyTaxRequest`: `tax_rate: float`, `.clamped_rate() -> float`.
  - `PolicyEventRequest`: `event`, `event_type` (aliased and validated).
  - `SimulationStatus`: `running: bool`, `tick: int`, `message: Optional[str]`.

---

## 5. Verification Method

To independently verify this specification and its compatibility with the project:

1. **Inspect Artifact Files**:
   - `view_file` on `c:\Users\Aditya S Yadav\Desktop\anything-to-website\my-game-economy-simulator\.agents\teamwork\m1_explorer_1\proposed_config.py`
   - `view_file` on `c:\Users\Aditya S Yadav\Desktop\anything-to-website\my-game-economy-simulator\.agents\teamwork\m1_explorer_1\proposed_models.py`

2. **Inspect Existing Test Contracts**:
   - Review `tests/conftest.py` lines 6-15, 18-67 to verify that `ItemState`, `AgentState`, and `EconomyState` signatures match `proposed_models.py` exactly.
   - Review `tests/test_tier1_features.py` lines 411-467 to verify `AgentDecision` validation and bounds.
   - Review `tests/test_tier2_boundaries.py` lines 348-415 to verify `quantity` $[1, 10]$ and `reasoning` $\le 120$ boundary tests.

3. **Downstream Worker Implementation Step**:
   When the Implementation Worker writes `src/config.py` and `src/models.py`:
   - Copy or adopt `proposed_config.py` -> `src/config.py`.
   - Copy or adopt `proposed_models.py` -> `src/models.py`.
   - Run the Tier 1 and Tier 2 test suites:
     ```bash
     pytest tests/test_tier1_features.py -k "schema or state or persona" -v
     pytest tests/test_tier2_boundaries.py -k "quantity or reasoning" -v
     ```
   - Invalidation condition: Any test failure importing from `src.models` or `src.config`, or any `pydantic.ValidationError` on valid payloads indicates a contract mismatch.
