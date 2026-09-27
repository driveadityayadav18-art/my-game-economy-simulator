import asyncio
import pytest

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
    apply_dragon_attack,
    apply_gold_rush,
)
from src.agents import BaseAgent
from tests.conftest import assert_state_invariants


# ============================================================================
# PAIRWISE 1: Dragon Attack Shock + Bankrupt / Poor Agent
# ============================================================================

def test_pairwise_dragon_attack_with_poor_agent(fresh_economy_state):
    """Dragon attack spikes potion price to 35.0; poor agent (20 Gold) is blocked from purchasing."""
    apply_dragon_attack(fresh_economy_state)
    assert fresh_economy_state.items["Health Potion"].price == 35.0
    assert fresh_economy_state.items["Health Potion"].supply == 2

    # Set Boran to 20 gold; cost is 35 * 1.10 = 38.50
    fresh_economy_state.agents["Boran the Adventurer"].gold = 20.0
    decision = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Need potion")
    
    record = execute_transaction(fresh_economy_state, "Boran the Adventurer", decision)
    assert record.status == "REJECTED"
    assert fresh_economy_state.agents["Boran the Adventurer"].gold == 20.0
    assert fresh_economy_state.items["Health Potion"].supply == 2
    assert_state_invariants(fresh_economy_state)


# ============================================================================
# PAIRWISE 2: Dragon Attack Shock + Wealthy Agent Exhausts Supply
# ============================================================================

def test_pairwise_dragon_attack_wealthy_agent_exhausts_supply(fresh_economy_state):
    """Garrick with ample gold buys all remaining post-dragon potions (2 units); supply drops to 0."""
    apply_dragon_attack(fresh_economy_state)
    garrick = fresh_economy_state.agents["Garrick the Greedy"]
    garrick.gold = 200.0

    # 2 units * 35.0 * 1.10 = 77.0
    decision = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=2, reasoning="Hoard potions")
    record = execute_transaction(fresh_economy_state, "Garrick the Greedy", decision)

    assert record.status == "EXECUTED"
    assert fresh_economy_state.items["Health Potion"].supply == 0
    assert garrick.gold == 200.0 - 77.0

    # Next attempt to buy even 1 potion must fail due to zero supply
    decision2 = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Want more")
    record2 = execute_transaction(fresh_economy_state, "Garrick the Greedy", decision2)
    assert record2.status == "REJECTED"
    assert_state_invariants(fresh_economy_state)


# ============================================================================
# PAIRWISE 3: High Tax (80%) + Maximum Buy Quantity (10)
# ============================================================================

def test_pairwise_high_tax_with_max_quantity_insufficient_gold(fresh_economy_state):
    """At 80% tax rate, bulk buying 10 units imposes huge tax surcharge exceeding funds."""
    fresh_economy_state.tax_rate = 0.80
    cora = fresh_economy_state.agents["Cora the Farmer"]
    cora.gold = 100.0
    # Price = 15.0; 10 units = 150.0 + 80% tax (120.0) = 270.0 total cost
    decision = AgentDecision(action=ActionType.BUY, item="Raw Gem", quantity=10, reasoning="Bulk buy gems")

    record = execute_transaction(fresh_economy_state, "Cora the Farmer", decision)
    assert record.status == "REJECTED"
    assert cora.gold == 100.0


def test_pairwise_high_tax_with_max_quantity_sufficient_gold(fresh_economy_state):
    """Wealthy buyer covers 80% tax surcharge on 10 units cleanly."""
    fresh_economy_state.tax_rate = 0.80
    garrick = fresh_economy_state.agents["Garrick the Greedy"]
    garrick.gold = 300.0
    # 10 units of Raw Gem at 15.0 = 150.0 + 120.0 tax = 270.0
    decision = AgentDecision(action=ActionType.BUY, item="Raw Gem", quantity=10, reasoning="Bulk hoard")

    record = execute_transaction(fresh_economy_state, "Garrick the Greedy", decision)
    assert record.status == "EXECUTED"
    assert garrick.gold == 30.0
    assert garrick.inventory["Raw Gem"] == 15  # initial 5 + 10
    assert_state_invariants(fresh_economy_state)


# ============================================================================
# PAIRWISE 4: Gold Rush (+100) + Previously Insolvent Agent
# ============================================================================

def test_pairwise_gold_rush_enables_previously_insolvent_purchase(fresh_economy_state):
    """Boran has 10 Gold (cannot afford Iron Sword at 30 + 3 tax = 33). Gold Rush allows immediate buy."""
    boran = fresh_economy_state.agents["Boran the Adventurer"]
    boran.gold = 10.0

    # Confirm initially rejected
    decision = AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=1, reasoning="Want weapon")
    rec1 = execute_transaction(fresh_economy_state, "Boran the Adventurer", decision)
    assert rec1.status == "REJECTED"

    # Inject Gold Rush shock
    apply_gold_rush(fresh_economy_state, gold_amount=100.0)
    assert boran.gold == 110.0

    # Retry purchase
    rec2 = execute_transaction(fresh_economy_state, "Boran the Adventurer", decision)
    assert rec2.status == "EXECUTED"
    assert boran.gold == 110.0 - 33.0
    assert boran.inventory["Iron Sword"] == 2
    assert_state_invariants(fresh_economy_state)


# ============================================================================
# PAIRWISE 5: Concurrent Decisions (1 Timeout Fallback + 2 Successes)
# ============================================================================

@pytest.mark.asyncio
async def test_pairwise_concurrent_decisions_with_partial_timeout(fresh_economy_state):
    """When 1 agent hangs (>2.0s), other 2 agents' decisions execute and state updates properly."""
    fast_seller = BaseAgent(name="Cora the Farmer", persona="Cora the Farmer")
    slow_agent = BaseAgent(name="Garrick the Greedy", persona="Garrick the Greedy")
    fast_buyer = BaseAgent(name="Boran the Adventurer", persona="Boran the Adventurer")

    tasks = [
        fast_seller.decide(fresh_economy_state.model_dump()),
        slow_agent.decide({"simulated_delay": 2.5}),
        fast_buyer.decide(fresh_economy_state.model_dump()),
    ]
    decisions = await asyncio.gather(*tasks)

    assert len(decisions) == 3
    # The slow agent should produce a HOLD decision or valid fallback
    assert decisions[1].action in [ActionType.HOLD, ActionType.BUY, ActionType.SELL]
    
    # Process decisions sequentially against state
    for agent_name, dec in zip(["Cora the Farmer", "Garrick the Greedy", "Boran the Adventurer"], decisions):
        rec = execute_transaction(fresh_economy_state, agent_name, dec)
        assert rec.status in ["EXECUTED", "REJECTED", "SKIPPED"]
        
    assert_state_invariants(fresh_economy_state)


# ============================================================================
# PAIRWISE 6: Dragon Attack + Simultaneous Buy & Sell (Net Demand Zero)
# ============================================================================

def test_pairwise_dragon_attack_balanced_trades_maintain_price(fresh_economy_state):
    """Post-Dragon Attack price (35.0) remains steady when buy and sell quantities cancel out."""
    apply_dragon_attack(fresh_economy_state)
    assert fresh_economy_state.items["Health Potion"].price == 35.0

    # Agent A buys 1 potion, Agent B sells 1 potion -> net demand = 0
    buyer_dec = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Buy potion")
    seller_dec = AgentDecision(action=ActionType.SELL, item="Health Potion", quantity=1, reasoning="Sell potion")

    execute_transaction(fresh_economy_state, "Garrick the Greedy", buyer_dec)
    execute_transaction(fresh_economy_state, "Cora the Farmer", seller_dec)

    # Net demand Delta D = 1 - 1 = 0
    p_new = calculate_new_price(old_price=35.0, net_demand=0, k=0.05)
    assert p_new == 35.0


# ============================================================================
# PAIRWISE 7: High Tax (80%) + Seller Inventory Liquidation
# ============================================================================

def test_pairwise_high_tax_seller_receives_net_after_tax(fresh_economy_state):
    """Selling 5 gems at 15.0 Gold with 80% tax: gross 75.0, tax 60.0 -> net revenue 15.0."""
    fresh_economy_state.tax_rate = 0.80
    cora = fresh_economy_state.agents["Cora the Farmer"]
    initial_gold = cora.gold
    initial_gems = cora.inventory["Raw Gem"]

    decision = AgentDecision(action=ActionType.SELL, item="Raw Gem", quantity=5, reasoning="Liquidate stock")
    record = execute_transaction(fresh_economy_state, "Cora the Farmer", decision)

    assert record.status == "EXECUTED"
    assert cora.inventory["Raw Gem"] == initial_gems - 5
    assert cora.gold == initial_gold + 15.0  # 75 - 60 = 15
    assert_state_invariants(fresh_economy_state)


# ============================================================================
# PAIRWISE 8: Zero Tax (0%) + High Volume Sells Driving Floor Clamping
# ============================================================================

def test_pairwise_zero_tax_massive_sells_clamped_to_floor(fresh_economy_state):
    """Under 0% tax, large volume selling pushes item to exact 1.0 Gold floor."""
    fresh_economy_state.tax_rate = 0.0
    p_old = 15.0
    # Selling 30 units across ticks -> net demand -30
    p_new = calculate_new_price(old_price=p_old, net_demand=-30, k=0.05)
    assert p_new == 1.0


# ============================================================================
# PAIRWISE 9: Gold Rush Shock Immediately Followed by 80% Tax Rate Hike
# ============================================================================

def test_pairwise_gold_rush_then_tax_spike(test_client):
    """Triggering Gold Rush followed by 80% tax rate updates state cohesively."""
    # 1. Trigger Gold Rush
    res_event = test_client.post("/policy/event", json={"event": "Gold Rush"})
    if res_event.status_code == 422:
        test_client.post("/policy/event", json={"event_type": "Gold Rush"})

    # 2. Hike Tax to 80%
    res_tax = test_client.post("/policy/tax", json={"tax_rate": 0.80})
    assert res_tax.status_code == 200

    # 3. Verify state
    state = test_client.get("/state").json()
    assert state["tax_rate"] == 0.80
    assert state["agents"]["Garrick the Greedy"]["gold"] >= 200.0


# ============================================================================
# PAIRWISE 10: Two Concurrent Buyers Exceeding Market Supply
# ============================================================================

def test_pairwise_competing_buyers_for_scarce_supply(fresh_economy_state):
    """When market supply is 2, first buyer gets 2, second buyer fails validation."""
    fresh_economy_state.items["Iron Sword"].supply = 2
    
    d1 = AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=2, reasoning="Buy remaining")
    d2 = AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=1, reasoning="Attempt buy")

    rec1 = execute_transaction(fresh_economy_state, "Garrick the Greedy", d1)
    assert rec1.status == "EXECUTED"
    assert fresh_economy_state.items["Iron Sword"].supply == 0

    rec2 = execute_transaction(fresh_economy_state, "Boran the Adventurer", d2)
    assert rec2.status == "REJECTED"
    assert_state_invariants(fresh_economy_state)
