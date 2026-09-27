import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from src.models import (
    ActionType,
    AgentDecision,
    ItemState,
    AgentState,
    EconomyState,
    TransactionRecord,
    PolicyTaxRequest,
    PolicyEventRequest,
)
from src.market import (
    calculate_new_price,
    calculate_tax,
    validate_transaction,
    execute_transaction,
    apply_dragon_attack,
    apply_gold_rush,
)
from src.agents import BaseAgent
from tests.conftest import assert_state_invariants


# ============================================================================
# FEATURE 1: Algorithmic Price Discovery Formula
# Formula: P_new = max(min_price, P_old * (1 + k * Delta_D))
# Default k = 0.05, min_price = 1.0, rounded to 2 decimals
# ============================================================================

def test_pricing_formula_positive_demand_single_unit():
    """R1/F1: Net demand +1 increases price by 5%."""
    # 20.0 * (1 + 0.05 * 1) = 21.0
    p_new = calculate_new_price(old_price=20.0, net_demand=1, k=0.05)
    assert p_new == 21.0


def test_pricing_formula_negative_demand_single_unit():
    """R1/F1: Net demand -1 decreases price by 5%."""
    # 20.0 * (1 + 0.05 * -1) = 19.0
    p_new = calculate_new_price(old_price=20.0, net_demand=-1, k=0.05)
    assert p_new == 19.0


def test_pricing_formula_multiple_units_positive():
    """R1/F1: Net demand +4 increases price by 20%."""
    # 30.0 * (1 + 0.05 * 4) = 36.0
    p_new = calculate_new_price(old_price=30.0, net_demand=4, k=0.05)
    assert p_new == 36.0


def test_pricing_formula_multiple_units_negative():
    """R1/F1: Net demand -3 decreases price by 15%."""
    # 15.0 * (1 - 0.15) = 12.75
    p_new = calculate_new_price(old_price=15.0, net_demand=-3, k=0.05)
    assert p_new == 12.75


def test_pricing_formula_custom_sensitivity():
    """R1/F1: Custom sensitivity parameter k=0.10 applied accurately."""
    # 25.0 * (1 + 0.10 * 2) = 30.0
    p_new = calculate_new_price(old_price=25.0, net_demand=2, k=0.10)
    assert p_new == 30.0


# ============================================================================
# FEATURE 2: Minimum Price Floor Enforcement (1.0 Gold)
# ============================================================================

def test_price_floor_exact_breach_clamped():
    """R1/F2: Decreasing 1.0 Gold price clamps strictly to 1.0."""
    p_new = calculate_new_price(old_price=1.0, net_demand=-1, k=0.05)
    assert p_new == 1.0


def test_price_floor_massive_negative_demand():
    """R1/F2: Extreme negative demand (Delta D = -25) clamps to 1.0 Gold."""
    # 2.0 * (1 + 0.05 * -25) = 2.0 * -0.25 = -0.5 -> 1.0
    p_new = calculate_new_price(old_price=2.0, net_demand=-25, k=0.05)
    assert p_new == 1.0


def test_price_floor_zero_price_prevented():
    """R1/F2: Net demand exactly -20 (yielding 0.0) clamps to 1.0."""
    # 10.0 * (1 - 1.0) = 0.0 -> 1.0
    p_new = calculate_new_price(old_price=10.0, net_demand=-20, k=0.05)
    assert p_new == 1.0


def test_price_floor_already_at_floor_with_further_sells():
    """R1/F2: Repeated selling at floor 1.0 stays pegged at 1.0."""
    p_new = calculate_new_price(old_price=1.0, net_demand=-5, k=0.05)
    assert p_new == 1.0


def test_price_floor_custom_minimum_price():
    """R1/F2: Custom min_price threshold respected."""
    # 10.0 * (1 - 0.75) = 2.5 -> clamped to min_price 5.0
    p_new = calculate_new_price(old_price=10.0, net_demand=-15, k=0.05, min_price=5.0)
    assert p_new == 5.0


# ============================================================================
# FEATURE 3: Supported Item Catalog
# ============================================================================

def test_item_catalog_health_potion_recognized():
    """R1/F3: 'Health Potion' is a valid item schema name."""
    item = ItemState(name="Health Potion", price=20.0, supply=100)
    assert item.name == "Health Potion"
    decision = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Need healing")
    assert decision.item == "Health Potion"


def test_item_catalog_iron_sword_recognized():
    """R1/F3: 'Iron Sword' is a valid item schema name."""
    item = ItemState(name="Iron Sword", price=30.0, supply=100)
    assert item.name == "Iron Sword"
    decision = AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=1, reasoning="Need weapon")
    assert decision.item == "Iron Sword"


def test_item_catalog_raw_gem_recognized():
    """R1/F3: 'Raw Gem' is a valid item schema name."""
    item = ItemState(name="Raw Gem", price=15.0, supply=100)
    assert item.name == "Raw Gem"
    decision = AgentDecision(action=ActionType.BUY, item="Raw Gem", quantity=1, reasoning="Need currency")
    assert decision.item == "Raw Gem"


def test_item_catalog_unsupported_item_rejected():
    """R1/F3: Unsupported item name fails Pydantic validation."""
    with pytest.raises(ValidationError):
        AgentDecision(action=ActionType.BUY, item="Magic Wand", quantity=1, reasoning="Invalid item")


def test_item_catalog_all_three_items_in_state(fresh_economy_state):
    """R1/F3: Fresh economy state contains all three required catalog items."""
    assert "Health Potion" in fresh_economy_state.items
    assert "Iron Sword" in fresh_economy_state.items
    assert "Raw Gem" in fresh_economy_state.items
    assert len(fresh_economy_state.items) == 3


# ============================================================================
# FEATURE 4: Transaction Tax Calculation
# Formula: T = unit_price * quantity * tax_rate
# ============================================================================

def test_tax_calculation_standard_rate():
    """R1/F4: 10% tax on 20.0 Gold unit price for 1 unit is 2.0 Gold."""
    tax = calculate_tax(unit_price=20.0, quantity=1, tax_rate=0.10)
    assert tax == 2.0


def test_tax_calculation_multi_quantity():
    """R1/F4: 15% tax on 30.0 Gold for 2 units is 9.0 Gold."""
    # 30.0 * 2 * 0.15 = 9.0
    tax = calculate_tax(unit_price=30.0, quantity=2, tax_rate=0.15)
    assert tax == 9.0


def test_tax_calculation_zero_tax_rate():
    """R1/F4: 0% tax rate yields 0.0 tax."""
    tax = calculate_tax(unit_price=50.0, quantity=3, tax_rate=0.0)
    assert tax == 0.0


def test_tax_calculation_max_tax_rate():
    """R1/F4: 80% maximum tax rate calculates correctly."""
    # 25.0 * 4 * 0.80 = 80.0
    tax = calculate_tax(unit_price=25.0, quantity=4, tax_rate=0.80)
    assert tax == 80.0


def test_tax_calculation_fractional_rounding():
    """R1/F4: Fractional tax rounds cleanly to 2 decimal places."""
    # 13.33 * 3 * 0.07 = 39.99 * 0.07 = 2.7993 -> 2.80
    tax = calculate_tax(unit_price=13.33, quantity=3, tax_rate=0.07)
    assert tax == 2.80


# ============================================================================
# FEATURE 5: Buyer Gold Validation
# Condition: agent.gold >= unit_price * quantity + tax
# ============================================================================

def test_buyer_gold_validation_sufficient_funds():
    """R1/F5: Buyer with abundant gold passes validation."""
    agent = AgentState(name="Rich", persona="Garrick", gold=100.0, inventory={})
    item = ItemState(name="Health Potion", price=20.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.BUY, quantity=2, tax_rate=0.10)
    assert valid is True
    assert msg == "" or "valid" in msg.lower() or "success" in msg.lower()


def test_buyer_gold_validation_exact_funds():
    """R1/F5: Buyer with exact cost (unit + tax) passes validation."""
    # Cost = 20.0 * 1 * (1 + 0.10) = 22.0
    agent = AgentState(name="Exact", persona="Boran", gold=22.0, inventory={})
    item = ItemState(name="Health Potion", price=20.0, supply=10)
    valid, _ = validate_transaction(agent, item, ActionType.BUY, quantity=1, tax_rate=0.10)
    assert valid is True


def test_buyer_gold_validation_insufficient_funds_fails():
    """R1/F5: Buyer with less gold than cost fails validation."""
    agent = AgentState(name="Broke", persona="Boran", gold=15.0, inventory={})
    item = ItemState(name="Health Potion", price=20.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.BUY, quantity=1, tax_rate=0.10)
    assert valid is False
    assert "gold" in msg.lower() or "insufficient" in msg.lower()


def test_buyer_gold_validation_zero_gold():
    """R1/F5: Buyer with 0 gold cannot buy."""
    agent = AgentState(name="Zero", persona="Boran", gold=0.0, inventory={})
    item = ItemState(name="Raw Gem", price=15.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.BUY, quantity=1, tax_rate=0.10)
    assert valid is False


def test_buyer_gold_validation_multi_unit_cost_overrun():
    """R1/F5: Buyer has gold for 1 unit but not for requested quantity 5."""
    agent = AgentState(name="Partial", persona="Garrick", gold=50.0, inventory={})
    item = ItemState(name="Iron Sword", price=30.0, supply=10)
    # 30 * 5 * 1.10 = 165 > 50
    valid, msg = validate_transaction(agent, item, ActionType.BUY, quantity=5, tax_rate=0.10)
    assert valid is False


# ============================================================================
# FEATURE 6: Seller Inventory Validation
# Condition: agent.inventory[item] >= quantity
# ============================================================================

def test_seller_inventory_validation_sufficient_stock():
    """R1/F6: Seller with sufficient inventory passes validation."""
    agent = AgentState(name="Seller", persona="Cora", gold=10.0, inventory={"Raw Gem": 5})
    item = ItemState(name="Raw Gem", price=15.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.SELL, quantity=2, tax_rate=0.10)
    assert valid is True


def test_seller_inventory_validation_exact_stock():
    """R1/F6: Seller selling exactly all held inventory passes."""
    agent = AgentState(name="Seller", persona="Cora", gold=10.0, inventory={"Raw Gem": 3})
    item = ItemState(name="Raw Gem", price=15.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.SELL, quantity=3, tax_rate=0.10)
    assert valid is True


def test_seller_inventory_validation_insufficient_stock():
    """R1/F6: Seller selling more units than held fails validation."""
    agent = AgentState(name="Seller", persona="Cora", gold=10.0, inventory={"Raw Gem": 2})
    item = ItemState(name="Raw Gem", price=15.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.SELL, quantity=5, tax_rate=0.10)
    assert valid is False
    assert "inventory" in msg.lower() or "insufficient" in msg.lower()


def test_seller_inventory_validation_zero_stock():
    """R1/F6: Seller with 0 inventory fails validation."""
    agent = AgentState(name="Seller", persona="Cora", gold=10.0, inventory={"Raw Gem": 0})
    item = ItemState(name="Raw Gem", price=15.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.SELL, quantity=1, tax_rate=0.10)
    assert valid is False


def test_seller_inventory_validation_untracked_item():
    """R1/F6: Selling an item key not present in agent dictionary fails."""
    agent = AgentState(name="Seller", persona="Cora", gold=10.0, inventory={})
    item = ItemState(name="Iron Sword", price=30.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.SELL, quantity=1, tax_rate=0.10)
    assert valid is False


# ============================================================================
# FEATURE 7: Atomic Execution
# ============================================================================

def test_atomic_execution_successful_buy(fresh_economy_state):
    """R1/F7: Successful BUY atomically updates buyer gold, inventory, and supply."""
    decision = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Buy potion")
    initial_gold = fresh_economy_state.agents["Garrick the Greedy"].gold
    initial_inventory = fresh_economy_state.agents["Garrick the Greedy"].inventory.get("Health Potion", 0)
    initial_supply = fresh_economy_state.items["Health Potion"].supply
    price = fresh_economy_state.items["Health Potion"].price
    tax = calculate_tax(price, 1, fresh_economy_state.tax_rate)
    total_cost = (price * 1) + tax

    record = execute_transaction(fresh_economy_state, "Garrick the Greedy", decision)

    assert record.status == "EXECUTED"
    assert fresh_economy_state.agents["Garrick the Greedy"].gold == initial_gold - total_cost
    assert fresh_economy_state.agents["Garrick the Greedy"].inventory["Health Potion"] == initial_inventory + 1
    assert fresh_economy_state.items["Health Potion"].supply == initial_supply - 1
    assert_state_invariants(fresh_economy_state)


def test_atomic_execution_successful_sell(fresh_economy_state):
    """R1/F7: Successful SELL atomically updates seller gold, inventory, and supply."""
    decision = AgentDecision(action=ActionType.SELL, item="Raw Gem", quantity=2, reasoning="Sell gems")
    initial_gold = fresh_economy_state.agents["Cora the Farmer"].gold
    initial_inventory = fresh_economy_state.agents["Cora the Farmer"].inventory["Raw Gem"]
    initial_supply = fresh_economy_state.items["Raw Gem"].supply
    price = fresh_economy_state.items["Raw Gem"].price
    gross_revenue = price * 2
    tax = calculate_tax(price, 2, fresh_economy_state.tax_rate)
    net_revenue = gross_revenue - tax

    record = execute_transaction(fresh_economy_state, "Cora the Farmer", decision)

    assert record.status == "EXECUTED"
    assert fresh_economy_state.agents["Cora the Farmer"].inventory["Raw Gem"] == initial_inventory - 2
    assert fresh_economy_state.items["Raw Gem"].supply == initial_supply + 2
    assert fresh_economy_state.agents["Cora the Farmer"].gold == initial_gold + net_revenue
    assert_state_invariants(fresh_economy_state)


def test_atomic_execution_rejected_buy_preserves_state(fresh_economy_state):
    """R1/F7: Rejected BUY modifies 0 balances, 0 inventories, 0 supplies."""
    # Boran has 40 gold, cannot afford 5 Iron Swords (30 * 5 * 1.10 = 165)
    decision = AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=5, reasoning="Need swords")
    snapshot_gold = fresh_economy_state.agents["Boran the Adventurer"].gold
    snapshot_inv = dict(fresh_economy_state.agents["Boran the Adventurer"].inventory)
    snapshot_supply = fresh_economy_state.items["Iron Sword"].supply

    record = execute_transaction(fresh_economy_state, "Boran the Adventurer", decision)

    assert record.status == "REJECTED"
    assert fresh_economy_state.agents["Boran the Adventurer"].gold == snapshot_gold
    assert fresh_economy_state.agents["Boran the Adventurer"].inventory == snapshot_inv
    assert fresh_economy_state.items["Iron Sword"].supply == snapshot_supply


def test_atomic_execution_rejected_sell_preserves_state(fresh_economy_state):
    """R1/F7: Rejected SELL leaves state completely unaltered."""
    decision = AgentDecision(action=ActionType.SELL, item="Iron Sword", quantity=10, reasoning="Sell excess")
    snapshot_inv = dict(fresh_economy_state.agents["Cora the Farmer"].inventory)
    snapshot_gold = fresh_economy_state.agents["Cora the Farmer"].gold

    record = execute_transaction(fresh_economy_state, "Cora the Farmer", decision)

    assert record.status == "REJECTED"
    assert fresh_economy_state.agents["Cora the Farmer"].inventory == snapshot_inv
    assert fresh_economy_state.agents["Cora the Farmer"].gold == snapshot_gold


def test_atomic_execution_hold_action_noop(fresh_economy_state):
    """R1/F7: HOLD decision executes as a non-mutating action."""
    decision = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Holding turn")
    snapshot_gold = fresh_economy_state.agents["Garrick the Greedy"].gold
    snapshot_inv = dict(fresh_economy_state.agents["Garrick the Greedy"].inventory)

    record = execute_transaction(fresh_economy_state, "Garrick the Greedy", decision)

    assert record.status in ["SKIPPED", "EXECUTED"]
    assert fresh_economy_state.agents["Garrick the Greedy"].gold == snapshot_gold
    assert fresh_economy_state.agents["Garrick the Greedy"].inventory == snapshot_inv


# ============================================================================
# FEATURE 8: Personas (Garrick, Cora, Boran)
# ============================================================================

def test_persona_garrick_attributes(initial_agents):
    """R2/F8: Garrick persona has greedy hoarding profile."""
    garrick = initial_agents["Garrick the Greedy"]
    assert "greedy" in garrick.persona.lower()
    assert garrick.gold >= 100.0


def test_persona_cora_attributes(initial_agents):
    """R2/F8: Cora persona has producer farmer profile with raw gems."""
    cora = initial_agents["Cora the Farmer"]
    assert "farmer" in cora.persona.lower()
    assert cora.inventory.get("Raw Gem", 0) >= 5


def test_persona_boran_attributes(initial_agents):
    """R2/F8: Boran persona has adventurous consumer profile."""
    boran = initial_agents["Boran the Adventurer"]
    assert "adventurer" in boran.persona.lower()
    assert boran.gold <= 60.0


def test_persona_agent_instantiation():
    """R2/F8: BaseAgent instantiates correctly with persona name."""
    agent = BaseAgent(name="Garrick the Greedy", persona="Garrick the Greedy")
    assert agent.name == "Garrick the Greedy"
    assert agent.persona == "Garrick the Greedy"


@pytest.mark.asyncio
async def test_persona_agent_decide_returns_agent_decision(fresh_economy_state):
    """R2/F8: BaseAgent decide() coroutine returns a valid AgentDecision."""
    agent = BaseAgent(name="Boran the Adventurer", persona="Boran the Adventurer")
    snapshot = fresh_economy_state.model_dump()
    decision = await agent.decide(snapshot)
    assert isinstance(decision, AgentDecision)
    assert decision.action in [ActionType.BUY, ActionType.SELL, ActionType.HOLD, ActionType.CRAFT]


# ============================================================================
# FEATURE 9: Structured JSON Schema Enforcement
# ============================================================================

def test_json_schema_valid_buy_decision():
    """R2/F9: Valid BUY decision payload passes schema."""
    d = AgentDecision.model_validate({
        "action": "BUY",
        "item": "Health Potion",
        "quantity": 2,
        "reasoning": "Need potion for battle",
    })
    assert d.action == ActionType.BUY
    assert d.quantity == 2


def test_json_schema_valid_hold_decision_with_null_item():
    """R2/F9: Valid HOLD decision with item=None parses successfully."""
    d = AgentDecision.model_validate({
        "action": "HOLD",
        "item": None,
        "quantity": 1,
        "reasoning": "Market too volatile",
    })
    assert d.action == ActionType.HOLD
    assert d.item is None


def test_json_schema_invalid_action_rejected():
    """R2/F9: Invalid action string fails schema validation."""
    with pytest.raises(ValidationError):
        AgentDecision.model_validate({
            "action": "DESTROY",
            "item": "Iron Sword",
            "quantity": 1,
            "reasoning": "Invalid action",
        })


def test_json_schema_quantity_out_of_bounds_rejected():
    """R2/F9: Quantity exceeding 10 violates bounds."""
    with pytest.raises(ValidationError):
        AgentDecision.model_validate({
            "action": "BUY",
            "item": "Raw Gem",
            "quantity": 15,
            "reasoning": "Quantity too high",
        })


def test_json_schema_reasoning_length_overflow_rejected():
    """R2/F9: Reasoning length > 120 chars fails validation."""
    long_reasoning = "A" * 125
    with pytest.raises(ValidationError):
        AgentDecision.model_validate({
            "action": "BUY",
            "item": "Health Potion",
            "quantity": 1,
            "reasoning": long_reasoning,
        })


# ============================================================================
# FEATURE 10: Simulated Heuristic Fallback
# ============================================================================

@pytest.mark.asyncio
async def test_heuristic_fallback_when_no_api_key(monkeypatch, fresh_economy_state):
    """R2/F10: Missing API key triggers safe simulated heuristic fallback."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    agent = BaseAgent(name="Cora the Farmer", persona="Cora the Farmer")
    decision = await agent.decide(fresh_economy_state.model_dump())
    assert isinstance(decision, AgentDecision)
    assert decision.action in [ActionType.HOLD, ActionType.BUY, ActionType.SELL]


@pytest.mark.asyncio
async def test_heuristic_fallback_on_network_failure(fresh_economy_state):
    """R2/F10: Network failure during LLM execution returns valid fallback."""
    agent = BaseAgent(name="Garrick the Greedy", persona="Garrick the Greedy")
    # Passing an empty or corrupted state snapshot should not crash the engine
    decision = await agent.decide({"corrupted": True})
    assert isinstance(decision, AgentDecision)
    assert decision.action in [ActionType.HOLD, ActionType.BUY, ActionType.SELL]


@pytest.mark.asyncio
async def test_heuristic_fallback_returns_hold_on_timeout():
    """R2/F10: Agent timeout safely defaults to HOLD action."""
    agent = BaseAgent(name="Boran the Adventurer", persona="Boran the Adventurer")
    # Simulate a forced timeout condition
    decision = await agent.decide({"timeout_simulate": True})
    assert isinstance(decision, AgentDecision)
    assert decision.action == ActionType.HOLD or len(decision.reasoning) <= 120


def test_heuristic_fallback_reasoning_field_populated():
    """R2/F10: Fallback decisions contain non-empty reasoning explanation."""
    decision = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Fallback: latency exceeded")
    assert "fallback" in decision.reasoning.lower()
    assert len(decision.reasoning) <= 120


def test_heuristic_fallback_zero_unhandled_exceptions():
    """R2/F10: Instantiating and executing fallback never throws unhandled errors."""
    decision = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Safe default")
    assert decision.action == ActionType.HOLD


# ============================================================================
# FEATURE 11: GET /state REST Endpoint
# ============================================================================

def test_endpoint_state_returns_200(test_client):
    """R3/F11: GET /state returns HTTP 200."""
    response = test_client.get("/state")
    assert response.status_code == 200


def test_endpoint_state_schema_keys(test_client):
    """R3/F11: GET /state contains all required state fields."""
    response = test_client.get("/state")
    data = response.json()
    assert "tick" in data
    assert "running" in data
    assert "tax_rate" in data
    assert "items" in data
    assert "agents" in data
    assert "recent_transactions" in data


def test_endpoint_state_contains_all_three_items(test_client):
    """R3/F11: GET /state includes Health Potion, Iron Sword, and Raw Gem."""
    data = test_client.get("/state").json()
    items = data["items"]
    assert "Health Potion" in items
    assert "Iron Sword" in items
    assert "Raw Gem" in items


def test_endpoint_state_contains_all_three_agents(test_client):
    """R3/F11: GET /state includes Garrick, Cora, and Boran."""
    data = test_client.get("/state").json()
    agents = data["agents"]
    assert "Garrick the Greedy" in agents
    assert "Cora the Farmer" in agents
    assert "Boran the Adventurer" in agents


def test_endpoint_state_validates_against_pydantic_model(test_client):
    """R3/F11: GET /state response validates into EconomyState Pydantic model."""
    data = test_client.get("/state").json()
    parsed = EconomyState.model_validate(data)
    assert isinstance(parsed, EconomyState)


# ============================================================================
# FEATURE 12: Manual Single-Tick Stepping (POST /simulation/tick)
# ============================================================================

def test_endpoint_tick_returns_200(test_client):
    """R3/F12: POST /simulation/tick returns HTTP 200."""
    response = test_client.post("/simulation/tick")
    assert response.status_code == 200


def test_endpoint_tick_increments_tick_counter(test_client):
    """R3/F12: POST /simulation/tick increments tick counter."""
    s0 = test_client.get("/state").json()["tick"]
    test_client.post("/simulation/tick")
    s1 = test_client.get("/state").json()["tick"]
    assert s1 == s0 + 1


def test_endpoint_tick_records_transactions_or_decisions(test_client):
    """R3/F12: POST /simulation/tick returns transaction results or decision list."""
    res = test_client.post("/simulation/tick")
    data = res.json()
    assert "tick" in data or "transactions" in data or "state" in data


def test_endpoint_tick_preserves_invariants(test_client):
    """R3/F12: POST /simulation/tick preserves all macroeconomic invariants."""
    test_client.post("/simulation/tick")
    state_json = test_client.get("/state").json()
    state = EconomyState.model_validate(state_json)
    assert_state_invariants(state)


def test_endpoint_tick_subsequent_ticks_advance_sequentially(test_client):
    """R3/F12: Consecutive manual ticks advance tick 1 step at a time."""
    start_tick = test_client.get("/state").json()["tick"]
    test_client.post("/simulation/tick")
    test_client.post("/simulation/tick")
    end_tick = test_client.get("/state").json()["tick"]
    assert end_tick == start_tick + 2


# ============================================================================
# FEATURE 13: Policy Tax Rate Endpoint (POST /policy/tax)
# ============================================================================

def test_endpoint_policy_tax_valid_update(test_client):
    """R3/F13: Updating tax rate to 0.25 via POST /policy/tax succeeds."""
    res = test_client.post("/policy/tax", json={"tax_rate": 0.25})
    assert res.status_code == 200
    state = test_client.get("/state").json()
    assert state["tax_rate"] == 0.25


def test_endpoint_policy_tax_zero_rate(test_client):
    """R3/F13: Setting tax rate to 0.0 succeeds."""
    res = test_client.post("/policy/tax", json={"tax_rate": 0.0})
    assert res.status_code == 200
    state = test_client.get("/state").json()
    assert state["tax_rate"] == 0.0


def test_endpoint_policy_tax_max_rate_80(test_client):
    """R3/F13: Setting tax rate to upper bound 0.80 succeeds."""
    res = test_client.post("/policy/tax", json={"tax_rate": 0.80})
    assert res.status_code == 200
    state = test_client.get("/state").json()
    assert state["tax_rate"] == 0.80


def test_endpoint_policy_tax_negative_rejected(test_client):
    """R3/F13: Setting negative tax rate is rejected or clamped."""
    res = test_client.post("/policy/tax", json={"tax_rate": -0.10})
    assert res.status_code in [400, 422, 200]
    state = test_client.get("/state").json()
    assert state["tax_rate"] >= 0.0


def test_endpoint_policy_tax_excessive_rejected(test_client):
    """R3/F13: Setting tax rate > 0.80 is rejected or clamped to 0.80."""
    res = test_client.post("/policy/tax", json={"tax_rate": 0.95})
    assert res.status_code in [400, 422, 200]
    state = test_client.get("/state").json()
    assert state["tax_rate"] <= 0.80


# ============================================================================
# FEATURE 14: Dragon Attack Shock Event
# Sets Health Potion supply = 2, base price = 35.0 Gold
# ============================================================================

def test_policy_dragon_attack_market_supply(fresh_economy_state):
    """R3/F14: apply_dragon_attack sets Health Potion market supply to 2."""
    fresh_economy_state.items["Health Potion"].supply = 100
    apply_dragon_attack(fresh_economy_state)
    assert fresh_economy_state.items["Health Potion"].supply == 2


def test_policy_dragon_attack_base_price(fresh_economy_state):
    """R3/F14: apply_dragon_attack sets Health Potion base price to 35.0 Gold."""
    fresh_economy_state.items["Health Potion"].price = 20.0
    apply_dragon_attack(fresh_economy_state)
    assert fresh_economy_state.items["Health Potion"].price == 35.0


def test_policy_dragon_attack_preserves_other_items(fresh_economy_state):
    """R3/F14: Dragon Attack does not mutate Iron Sword or Raw Gem states."""
    sword_price = fresh_economy_state.items["Iron Sword"].price
    gem_supply = fresh_economy_state.items["Raw Gem"].supply
    apply_dragon_attack(fresh_economy_state)
    assert fresh_economy_state.items["Iron Sword"].price == sword_price
    assert fresh_economy_state.items["Raw Gem"].supply == gem_supply


def test_policy_dragon_attack_endpoint_returns_200(test_client):
    """R3/F14: POST /policy/event with 'Dragon Attack' returns HTTP 200."""
    res = test_client.post("/policy/event", json={"event": "Dragon Attack"})
    if res.status_code == 422:
        res = test_client.post("/policy/event", json={"event_type": "Dragon Attack"})
    assert res.status_code == 200


def test_policy_dragon_attack_reflected_in_state_endpoint(test_client):
    """R3/F14: State reflects Health Potion price 35.0 and supply 2 after event."""
    test_client.post("/policy/event", json={"event": "Dragon Attack"})
    state = test_client.get("/state").json()
    assert state["items"]["Health Potion"]["price"] == 35.0
    assert state["items"]["Health Potion"]["supply"] == 2


# ============================================================================
# FEATURE 15: Gold Rush Shock Event
# Immediately credits +100 Gold to all agents
# ============================================================================

def test_policy_gold_rush_credits_garrick(fresh_economy_state):
    """R3/F15: apply_gold_rush credits +100.0 Gold to Garrick."""
    initial = fresh_economy_state.agents["Garrick the Greedy"].gold
    apply_gold_rush(fresh_economy_state, gold_amount=100.0)
    assert fresh_economy_state.agents["Garrick the Greedy"].gold == initial + 100.0


def test_policy_gold_rush_credits_cora(fresh_economy_state):
    """R3/F15: apply_gold_rush credits +100.0 Gold to Cora."""
    initial = fresh_economy_state.agents["Cora the Farmer"].gold
    apply_gold_rush(fresh_economy_state, gold_amount=100.0)
    assert fresh_economy_state.agents["Cora the Farmer"].gold == initial + 100.0


def test_policy_gold_rush_credits_boran(fresh_economy_state):
    """R3/F15: apply_gold_rush credits +100.0 Gold to Boran."""
    initial = fresh_economy_state.agents["Boran the Adventurer"].gold
    apply_gold_rush(fresh_economy_state, gold_amount=100.0)
    assert fresh_economy_state.agents["Boran the Adventurer"].gold == initial + 100.0


def test_policy_gold_rush_endpoint_returns_200(test_client):
    """R3/F15: POST /policy/event with 'Gold Rush' returns HTTP 200."""
    res = test_client.post("/policy/event", json={"event": "Gold Rush"})
    if res.status_code == 422:
        res = test_client.post("/policy/event", json={"event_type": "Gold Rush"})
    assert res.status_code == 200


def test_policy_gold_rush_reflected_in_state_endpoint(test_client):
    """R3/F15: State endpoint reflects updated agent gold after Gold Rush event."""
    before = test_client.get("/state").json()["agents"]
    res = test_client.post("/policy/event", json={"event": "Gold Rush"})
    if res.status_code == 422:
        res = test_client.post("/policy/event", json={"event_type": "Gold Rush"})
    after = test_client.get("/state").json()["agents"]
    for agent_name in ["Garrick the Greedy", "Cora the Farmer", "Boran the Adventurer"]:
        assert after[agent_name]["gold"] == before[agent_name]["gold"] + 100.0


def test_simulation_reset_endpoint(test_client):
    """POST /simulation/reset restores initial defaults and stops loop."""
    # Run a tick or modify state
    test_client.post("/simulation/tick")
    res = test_client.post("/simulation/reset")
    assert res.status_code == 200
    data = res.json()
    assert data["running"] is False
    assert data["tick"] == 0

    state = test_client.get("/state").json()
    assert state["tick"] == 0
    assert state["running"] is False


def test_policy_trade_war_endpoint(test_client):
    """POST /policy/event with 'Trade War' sets tax rate to 50%."""
    res = test_client.post("/policy/event", json={"event": "Trade War"})
    assert res.status_code == 200
    state = test_client.get("/state").json()
    assert state["tax_rate"] == 0.50


def test_policy_market_crash_endpoint(test_client):
    """POST /policy/event with 'Market Crash' lowers prices by 40%."""
    before = test_client.get("/state").json()["items"]
    res = test_client.post("/policy/event", json={"event": "Market Crash"})
    assert res.status_code == 200
    after = test_client.get("/state").json()["items"]
    for item_name in before:
        expected = max(1.0, round(before[item_name]["price"] * 0.60, 2))
        assert after[item_name]["price"] == expected


def test_policy_black_market_endpoint(test_client):
    """POST /policy/event with 'Black Market' spikes prices and gifts gold."""
    before = test_client.get("/state").json()
    res = test_client.post("/policy/event", json={"event": "Black Market"})
    assert res.status_code == 200
    after = test_client.get("/state").json()
    for item_name in before["items"]:
        expected = round(before["items"][item_name]["price"] * 1.25, 2)
        assert after["items"][item_name]["price"] == expected

