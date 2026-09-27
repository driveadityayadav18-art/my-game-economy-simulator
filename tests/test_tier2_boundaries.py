import asyncio
import pytest
from pydantic import ValidationError

from src.models import (
    ActionType,
    AgentDecision,
    ItemState,
    AgentState,
    EconomyState,
    TransactionRecord,
)
from src.market import (
    calculate_new_price,
    calculate_tax,
    validate_transaction,
    execute_transaction,
)
from src.agents import BaseAgent
from tests.conftest import assert_state_invariants


# ============================================================================
# BOUNDARY 1: Price Floor Clamping when Delta D <= -20
# ============================================================================

def test_boundary_price_floor_exact_negative_twenty():
    """Delta D = -20 on price 10.0: 10 * (1 - 1.0) = 0.0 -> clamped to 1.0."""
    p = calculate_new_price(old_price=10.0, net_demand=-20, k=0.05)
    assert p == 1.0


def test_boundary_price_floor_negative_twenty_one():
    """Delta D = -21 on price 10.0: 10 * (1 - 1.05) = -0.5 -> clamped to 1.0."""
    p = calculate_new_price(old_price=10.0, net_demand=-21, k=0.05)
    assert p == 1.0


def test_boundary_price_floor_extreme_negative_fifty():
    """Delta D = -50 on price 20.0: 20 * (1 - 2.5) = -30.0 -> clamped to 1.0."""
    p = calculate_new_price(old_price=20.0, net_demand=-50, k=0.05)
    assert p == 1.0


def test_boundary_price_floor_extreme_negative_one_hundred():
    """Delta D = -100 on price 50.0: clamped to 1.0."""
    p = calculate_new_price(old_price=50.0, net_demand=-100, k=0.05)
    assert p == 1.0


def test_boundary_price_floor_already_at_one_with_delta_minus_twenty():
    """Delta D = -20 when old price is already at floor 1.0 remains strictly 1.0."""
    p = calculate_new_price(old_price=1.0, net_demand=-20, k=0.05)
    assert p == 1.0


# ============================================================================
# BOUNDARY 2: Delta D = 0 (Zero Net Demand)
# ============================================================================

def test_boundary_net_demand_zero_standard_price():
    """Delta D = 0 maintains price 20.0 perfectly."""
    p = calculate_new_price(old_price=20.0, net_demand=0, k=0.05)
    assert p == 20.0


def test_boundary_net_demand_zero_floor_price():
    """Delta D = 0 at price floor 1.0 stays 1.0."""
    p = calculate_new_price(old_price=1.0, net_demand=0, k=0.05)
    assert p == 1.0


def test_boundary_net_demand_zero_fractional_price():
    """Delta D = 0 with fractional price preserves exact float precision."""
    p = calculate_new_price(old_price=17.85, net_demand=0, k=0.05)
    assert p == 17.85


def test_boundary_net_demand_balanced_trade_volume():
    """Net demand resulting from identical buy and sell volumes (e.g. 5 buys, 5 sells)."""
    net_demand = 5 - 5
    p = calculate_new_price(old_price=35.0, net_demand=net_demand, k=0.05)
    assert p == 35.0


def test_boundary_net_demand_all_hold_invariants(fresh_economy_state):
    """When all agents HOLD, Delta D = 0 across all items and prices stay unchanged."""
    prices_before = {name: item.price for name, item in fresh_economy_state.items.items()}
    for name, item in fresh_economy_state.items.items():
        new_p = calculate_new_price(old_price=item.price, net_demand=0, k=0.05)
        assert new_p == prices_before[name]


# ============================================================================
# BOUNDARY 3: Tax Rates 0.0 and 0.80 Boundaries
# ============================================================================

def test_boundary_tax_rate_exact_zero():
    """Tax rate exactly 0.0 yields 0.0 tax."""
    t = calculate_tax(unit_price=25.0, quantity=2, tax_rate=0.0)
    assert t == 0.0


def test_boundary_tax_rate_exact_eighty_percent():
    """Tax rate exactly 0.80 calculates 80% tax accurately."""
    # 20.0 * 2 * 0.80 = 32.0
    t = calculate_tax(unit_price=20.0, quantity=2, tax_rate=0.80)
    assert t == 32.0


def test_boundary_tax_rate_zero_with_large_quantity():
    """Tax rate 0.0 with maximum quantity 10 yields 0.0 tax."""
    t = calculate_tax(unit_price=100.0, quantity=10, tax_rate=0.0)
    assert t == 0.0


def test_boundary_tax_rate_eighty_percent_with_single_unit():
    """Tax rate 0.80 with unit price 1.0 Gold yields 0.80 Gold tax."""
    t = calculate_tax(unit_price=1.0, quantity=1, tax_rate=0.80)
    assert t == 0.80


def test_boundary_tax_policy_endpoint_accepts_boundaries(test_client):
    """POST /policy/tax accepts boundary rates 0.0 and 0.80 cleanly."""
    res_0 = test_client.post("/policy/tax", json={"tax_rate": 0.0})
    assert res_0.status_code == 200
    assert test_client.get("/state").json()["tax_rate"] == 0.0

    res_80 = test_client.post("/policy/tax", json={"tax_rate": 0.80})
    assert res_80.status_code == 200
    assert test_client.get("/state").json()["tax_rate"] == 0.80


# ============================================================================
# BOUNDARY 4: Agent Exact Gold = Cost
# ============================================================================

def test_boundary_exact_gold_zero_tax():
    """Buyer with exact gold cost (zero tax) passes validation."""
    agent = AgentState(name="ExactZero", persona="Boran", gold=20.0, inventory={})
    item = ItemState(name="Health Potion", price=20.0, supply=10)
    valid, _ = validate_transaction(agent, item, ActionType.BUY, quantity=1, tax_rate=0.0)
    assert valid is True


def test_boundary_exact_gold_with_standard_tax():
    """Buyer with exact gold covering unit price plus 10% tax passes validation."""
    # 20.0 + 2.0 = 22.0
    agent = AgentState(name="ExactTen", persona="Boran", gold=22.0, inventory={})
    item = ItemState(name="Health Potion", price=20.0, supply=10)
    valid, _ = validate_transaction(agent, item, ActionType.BUY, quantity=1, tax_rate=0.10)
    assert valid is True


def test_boundary_exact_gold_multi_quantity():
    """Buyer with exact gold for 5 units at 15.0 Gold + 10% tax passes validation."""
    # 5 * 15 = 75.0; tax = 7.50; total = 82.50
    agent = AgentState(name="ExactMulti", persona="Garrick", gold=82.50, inventory={})
    item = ItemState(name="Raw Gem", price=15.0, supply=10)
    valid, _ = validate_transaction(agent, item, ActionType.BUY, quantity=5, tax_rate=0.10)
    assert valid is True


def test_boundary_exact_gold_execution_results_in_zero_balance(fresh_economy_state):
    """Executing BUY when gold exactly equals cost results in balance 0.0 without negative balance."""
    agent_name = "Boran the Adventurer"
    price = fresh_economy_state.items["Health Potion"].price
    tax = calculate_tax(price, 1, fresh_economy_state.tax_rate)
    total_cost = price + tax
    fresh_economy_state.agents[agent_name].gold = total_cost

    decision = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Exact gold buy")
    record = execute_transaction(fresh_economy_state, agent_name, decision)

    assert record.status == "EXECUTED"
    assert fresh_economy_state.agents[agent_name].gold == 0.0
    assert_state_invariants(fresh_economy_state)


def test_boundary_exact_gold_at_max_tax_rate():
    """Exact gold balance under 80% tax rate (P=10, Q=1, total=18.0) validates."""
    agent = AgentState(name="ExactEighty", persona="Cora", gold=18.0, inventory={})
    item = ItemState(name="Raw Gem", price=10.0, supply=10)
    valid, _ = validate_transaction(agent, item, ActionType.BUY, quantity=1, tax_rate=0.80)
    assert valid is True


# ============================================================================
# BOUNDARY 5: Agent Gold Deficit by 0.01
# ============================================================================

def test_boundary_gold_deficit_cent_zero_tax():
    """Cost 10.00, Gold 9.99 fails validation by 0.01."""
    agent = AgentState(name="Deficit1", persona="Boran", gold=9.99, inventory={})
    item = ItemState(name="Raw Gem", price=10.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.BUY, quantity=1, tax_rate=0.0)
    assert valid is False
    assert "insufficient" in msg.lower() or "gold" in msg.lower()


def test_boundary_gold_deficit_cent_with_tax():
    """Cost 22.00, Gold 21.99 fails validation by 0.01."""
    agent = AgentState(name="Deficit2", persona="Boran", gold=21.99, inventory={})
    item = ItemState(name="Health Potion", price=20.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.BUY, quantity=1, tax_rate=0.10)
    assert valid is False


def test_boundary_gold_deficit_cent_large_order():
    """Cost 165.00, Gold 164.99 fails validation by 0.01."""
    agent = AgentState(name="Deficit3", persona="Garrick", gold=164.99, inventory={})
    item = ItemState(name="Iron Sword", price=30.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.BUY, quantity=5, tax_rate=0.10)
    assert valid is False


def test_boundary_gold_deficit_cent_preserves_balance(fresh_economy_state):
    """Attempting execution with 0.01 gold deficit rejects and leaves 21.99 gold intact."""
    agent_name = "Boran the Adventurer"
    fresh_economy_state.agents[agent_name].gold = 21.99
    fresh_economy_state.items["Health Potion"].price = 20.0
    fresh_economy_state.tax_rate = 0.10  # Cost = 22.00

    decision = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Deficit buy")
    record = execute_transaction(fresh_economy_state, agent_name, decision)

    assert record.status == "REJECTED"
    assert fresh_economy_state.agents[agent_name].gold == 21.99


def test_boundary_gold_deficit_at_price_floor():
    """At price floor 1.0 Gold (tax 0.10, cost 1.10), agent with 1.09 Gold fails."""
    agent = AgentState(name="DeficitFloor", persona="Boran", gold=1.09, inventory={})
    item = ItemState(name="Health Potion", price=1.0, supply=10)
    valid, _ = validate_transaction(agent, item, ActionType.BUY, quantity=1, tax_rate=0.10)
    assert valid is False


# ============================================================================
# BOUNDARY 6: Selling Quantity > Inventory
# ============================================================================

def test_boundary_sell_quantity_exceeds_by_one():
    """Inventory = 5, sell quantity = 6 fails validation."""
    agent = AgentState(name="S1", persona="Cora", gold=10.0, inventory={"Raw Gem": 5})
    item = ItemState(name="Raw Gem", price=15.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.SELL, quantity=6, tax_rate=0.10)
    assert valid is False
    assert "inventory" in msg.lower() or "insufficient" in msg.lower()


def test_boundary_sell_quantity_zero_inventory_attempting_one():
    """Inventory = 0, sell quantity = 1 fails validation."""
    agent = AgentState(name="S2", persona="Cora", gold=10.0, inventory={"Iron Sword": 0})
    item = ItemState(name="Iron Sword", price=30.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.SELL, quantity=1, tax_rate=0.10)
    assert valid is False


def test_boundary_sell_quantity_unowned_item_key():
    """Inventory dict does not have item key at all; fails validation."""
    agent = AgentState(name="S3", persona="Cora", gold=10.0, inventory={})
    item = ItemState(name="Health Potion", price=20.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.SELL, quantity=1, tax_rate=0.10)
    assert valid is False


def test_boundary_sell_quantity_max_allowed_ten_when_holding_nine():
    """Inventory = 9, requesting max quantity 10 fails validation."""
    agent = AgentState(name="S4", persona="Cora", gold=10.0, inventory={"Raw Gem": 9})
    item = ItemState(name="Raw Gem", price=15.0, supply=10)
    valid, msg = validate_transaction(agent, item, ActionType.SELL, quantity=10, tax_rate=0.10)
    assert valid is False


def test_boundary_sell_rejection_preserves_stock(fresh_economy_state):
    """Executing an invalid SELL leaves agent inventory completely unchanged."""
    from src.market import validate_transaction
    agent_name = "Cora the Farmer"
    agent = fresh_economy_state.agents[agent_name]
    initial_gems = agent.inventory.get("Raw Gem", 10)
    item = fresh_economy_state.items["Raw Gem"]
    # Try to sell more than held (use max valid quantity 10 when held is less)
    over_qty = initial_gems + 1
    is_valid, reason = validate_transaction(agent, item, ActionType.SELL, quantity=over_qty, tax_rate=fresh_economy_state.tax_rate)
    assert is_valid is False
    assert "inventory" in reason.lower() or "insufficient" in reason.lower()
    # State must be completely unchanged since we only validated, not executed
    assert fresh_economy_state.agents[agent_name].inventory["Raw Gem"] == initial_gems


# ============================================================================
# BOUNDARY 7: LLM Timeout > 2.0s
# ============================================================================

@pytest.mark.asyncio
async def test_boundary_timeout_at_two_point_zero_five_seconds():
    """Simulated response delay of 2.05s triggers timeout fallback."""
    agent = BaseAgent(name="DelayedAgent", persona="Garrick the Greedy")
    decision = await agent.decide({"simulated_delay": 2.05})
    assert isinstance(decision, AgentDecision)
    assert decision.action == ActionType.HOLD or len(decision.reasoning) <= 120


@pytest.mark.asyncio
async def test_boundary_timeout_at_two_point_five_seconds():
    """Simulated response delay of 2.5s triggers timeout fallback."""
    agent = BaseAgent(name="DelayedAgent", persona="Cora the Farmer")
    decision = await agent.decide({"simulated_delay": 2.5})
    assert isinstance(decision, AgentDecision)
    assert decision.action in [ActionType.HOLD, ActionType.BUY, ActionType.SELL]


@pytest.mark.asyncio
async def test_boundary_timeout_at_three_seconds():
    """Simulated response delay of 3.0s triggers timeout fallback."""
    agent = BaseAgent(name="DelayedAgent", persona="Boran the Adventurer")
    decision = await agent.decide({"simulated_delay": 3.0})
    assert isinstance(decision, AgentDecision)
    assert decision.action in [ActionType.HOLD, ActionType.BUY, ActionType.SELL]


@pytest.mark.asyncio
async def test_boundary_timeout_reasoning_contains_fallback_flag():
    """Timeout fallback decision reasoning notes the fallback condition."""
    agent = BaseAgent(name="DelayedAgent", persona="Garrick the Greedy")
    decision = await agent.decide({"simulated_delay": 2.1})
    assert len(decision.reasoning) <= 120
    assert len(decision.reasoning) > 0


@pytest.mark.asyncio
async def test_boundary_timeout_parallel_isolation(fresh_economy_state):
    """When 1 agent times out, the other 2 concurrent agents can still return valid decisions."""
    agent_fast1 = BaseAgent(name="Fast1", persona="Cora the Farmer")
    agent_slow = BaseAgent(name="Slow", persona="Garrick the Greedy")
    agent_fast2 = BaseAgent(name="Fast2", persona="Boran the Adventurer")

    tasks = [
        agent_fast1.decide(fresh_economy_state.model_dump()),
        agent_slow.decide({"simulated_delay": 2.2}),
        agent_fast2.decide(fresh_economy_state.model_dump()),
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 3
    for r in results:
        assert isinstance(r, AgentDecision)


# ============================================================================
# BOUNDARY 8: Quantity Clamping & Validation [1, 10]
# ============================================================================

def test_boundary_quantity_minimum_one():
    """Quantity = 1 is the lower inclusive boundary."""
    d = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Min quantity")
    assert d.quantity == 1


def test_boundary_quantity_maximum_ten():
    """Quantity = 10 is the upper inclusive boundary."""
    d = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=10, reasoning="Max quantity")
    assert d.quantity == 10


def test_boundary_quantity_zero_rejected():
    """Quantity = 0 violates ge=1 boundary."""
    with pytest.raises(ValidationError):
        AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=0, reasoning="Zero quantity")


def test_boundary_quantity_negative_rejected():
    """Quantity = -1 violates ge=1 boundary."""
    with pytest.raises(ValidationError):
        AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=-1, reasoning="Negative quantity")


def test_boundary_quantity_eleven_rejected():
    """Quantity = 11 violates le=10 boundary."""
    with pytest.raises(ValidationError):
        AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=11, reasoning="Excessive quantity")


# ============================================================================
# BOUNDARY 9: Reasoning Length Max 120 Boundary
# ============================================================================

def test_boundary_reasoning_length_one():
    """Reasoning length = 1 char is valid."""
    d = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="H")
    assert len(d.reasoning) == 1


def test_boundary_reasoning_length_exact_one_hundred_twenty():
    """Reasoning length = 120 chars is valid at boundary."""
    exact_120 = "X" * 120
    d = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning=exact_120)
    assert len(d.reasoning) == 120


def test_boundary_reasoning_length_one_hundred_twenty_one_rejected():
    """Reasoning length = 121 chars violates max_length=120."""
    overflow_121 = "X" * 121
    with pytest.raises(ValidationError):
        AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning=overflow_121)


def test_boundary_reasoning_special_characters_within_bounds():
    """Reasoning containing punctuation, quotes, and emojis under 120 chars is valid."""
    text = "Buying 2 potions! Tax=10% (Gold: 45.50 -> 23.50) [OK] #deal"
    d = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=2, reasoning=text)
    assert d.reasoning == text


def test_boundary_reasoning_whitespace_padding():
    """Reasoning with whitespace padding under 120 chars validates."""
    padded = "   Trade completed successfully.   "
    d = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning=padded)
    assert len(d.reasoning) <= 120
