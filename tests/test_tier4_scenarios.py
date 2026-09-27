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
from tests.conftest import assert_state_invariants


# ============================================================================
# SCENARIO 1: 5-Tick Continuous Trading Loop
# ============================================================================

def test_scenario_five_tick_continuous_trading_loop(fresh_economy_state):
    """Executes a 5-tick continuous simulation loop verifying state evolution and invariants."""
    state = fresh_economy_state
    k = 0.05

    # Define deterministic actions for 5 ticks
    scripted_turns = [
        # Tick 1: Cora sells 2 gems; Garrick buys 1 potion; Boran holds
        [
            ("Cora the Farmer", AgentDecision(action=ActionType.SELL, item="Raw Gem", quantity=2, reasoning="Sell raw crop")),
            ("Garrick the Greedy", AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Early stockpile")),
            ("Boran the Adventurer", AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Waiting")),
        ],
        # Tick 2: Cora sells 1 gem; Garrick buys 2 gems; Boran buys 1 potion
        [
            ("Cora the Farmer", AgentDecision(action=ActionType.SELL, item="Raw Gem", quantity=1, reasoning="Sell gem")),
            ("Garrick the Greedy", AgentDecision(action=ActionType.BUY, item="Raw Gem", quantity=2, reasoning="Hoard gems")),
            ("Boran the Adventurer", AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Buy potion")),
        ],
        # Tick 3: Garrick buys 1 sword; Cora holds; Boran holds
        [
            ("Garrick the Greedy", AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=1, reasoning="Acquire weapon")),
            ("Cora the Farmer", AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Resting")),
            ("Boran the Adventurer", AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Resting")),
        ],
        # Tick 4: Boran sells 1 sword; Cora sells 1 gem; Garrick holds
        [
            ("Boran the Adventurer", AgentDecision(action=ActionType.SELL, item="Iron Sword", quantity=1, reasoning="Sell sidearm")),
            ("Cora the Farmer", AgentDecision(action=ActionType.SELL, item="Raw Gem", quantity=1, reasoning="Steady income")),
            ("Garrick the Greedy", AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Observing")),
        ],
        # Tick 5: Cora holds; Garrick holds; Boran holds
        [
            ("Cora the Farmer", AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="End cycle")),
            ("Garrick the Greedy", AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="End cycle")),
            ("Boran the Adventurer", AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="End cycle")),
        ],
    ]

    for turn_idx, turn_decisions in enumerate(scripted_turns, start=1):
        state.tick = turn_idx
        net_demands = {item_name: 0 for item_name in state.items}

        for agent_name, decision in turn_decisions:
            record = execute_transaction(state, agent_name, decision)

            if record.status == "EXECUTED" and decision.item:
                if decision.action == ActionType.BUY:
                    net_demands[decision.item] += decision.quantity
                elif decision.action == ActionType.SELL:
                    net_demands[decision.item] -= decision.quantity

        # Update market prices based on net demand for the tick
        for item_name, item in state.items.items():
            delta_d = net_demands[item_name]
            item.price = calculate_new_price(item.price, delta_d, k=k)

        # Invariant checks after every tick
        assert state.tick == turn_idx
        assert_state_invariants(state)

    # Final post-5-tick checks
    assert state.tick == 5
    assert len(state.recent_transactions) == 15
    # Potions had net buy pressure (bought in ticks 1 and 2), price should be >= starting 20.0
    assert state.items["Health Potion"].price >= 20.0


# ============================================================================
# SCENARIO 2: Dragon Attack Shock and Subsequent Recovery
# ============================================================================

def test_scenario_dragon_attack_shock_and_recovery(fresh_economy_state):
    """Tests economic reaction to Dragon Attack shock: price spike, scarcity, and stabilization."""
    state = fresh_economy_state

    # Phase 1: Pre-shock equilibrium
    assert state.items["Health Potion"].price == 20.0
    assert state.items["Health Potion"].supply == 100

    # Phase 2: Shock occurs
    apply_dragon_attack(state)
    assert state.items["Health Potion"].price == 35.0
    assert state.items["Health Potion"].supply == 2

    # Phase 3: Immediate buyer panic (Garrick buys 1 of the 2 remaining potions)
    buy_dec = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Panic buy potion")
    rec_buy = execute_transaction(state, "Garrick the Greedy", buy_dec)
    assert rec_buy.status == "EXECUTED"
    assert state.items["Health Potion"].supply == 1

    # Price discovery reflects net demand +1
    state.items["Health Potion"].price = calculate_new_price(35.0, net_demand=1, k=0.05)
    # 35.0 * 1.05 = 36.75
    assert state.items["Health Potion"].price == 36.75

    # Phase 4: Emergency supply release (Cora sells 2 potions to capitalize on high price)
    cora = state.agents["Cora the Farmer"]
    cora.inventory["Health Potion"] = 2
    sell_dec = AgentDecision(action=ActionType.SELL, item="Health Potion", quantity=2, reasoning="Sell at peak")
    rec_sell = execute_transaction(state, "Cora the Farmer", sell_dec)
    assert rec_sell.status == "EXECUTED"
    assert state.items["Health Potion"].supply == 3  # 1 + 2

    # Price cools down with net demand -2
    state.items["Health Potion"].price = calculate_new_price(36.75, net_demand=-2, k=0.05)
    # 36.75 * 0.90 = 33.08
    assert state.items["Health Potion"].price == 33.08
    assert_state_invariants(state)


# ============================================================================
# SCENARIO 3: Tax Hike Inducing Trade Contraction
# ============================================================================

def test_scenario_tax_hike_trade_contraction(fresh_economy_state):
    """Sudden tax rate increase from 10% to 75% causes trade failure for marginal agents."""
    state = fresh_economy_state
    boran = state.agents["Boran the Adventurer"]
    boran.gold = 35.0

    # Under 10% tax, Boran can afford 1 Iron Sword (30.0 + 3.0 = 33.0 <= 35.0)
    decision = AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=1, reasoning="Equip weapon")
    valid_low_tax, _ = validate_transaction(boran, state.items["Iron Sword"], decision.action, decision.quantity, 0.10)
    assert valid_low_tax is True

    # Policy intervention: Tax hike to 75%
    state.tax_rate = 0.75
    # Total cost now = 30.0 * (1 + 0.75) = 52.50 > 35.0
    valid_high_tax, err_msg = validate_transaction(boran, state.items["Iron Sword"], decision.action, decision.quantity, 0.75)
    assert valid_high_tax is False

    # Execution is rejected cleanly without balance modification
    rec = execute_transaction(state, "Boran the Adventurer", decision)
    assert rec.status == "REJECTED"
    assert boran.gold == 35.0
    assert_state_invariants(state)


# ============================================================================
# SCENARIO 4: Gold Rush Wealth Injection and Consumption Wave
# ============================================================================

def test_scenario_gold_rush_consumption_wave(fresh_economy_state):
    """Gold Rush adds +100 Gold to all agents, triggering an aggregate consumption wave and price increases."""
    state = fresh_economy_state
    starting_golds = {name: agent.gold for name, agent in state.agents.items()}

    # Trigger Gold Rush
    apply_gold_rush(state, gold_amount=100.0)
    for name, agent in state.agents.items():
        assert agent.gold == starting_golds[name] + 100.0

    # Agents now embark on an aggressive buying spree
    purchases = [
        ("Garrick the Greedy", AgentDecision(action=ActionType.BUY, item="Raw Gem", quantity=5, reasoning="Hoard gems with windfall")),
        ("Cora the Farmer", AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=2, reasoning="Stockpile potions")),
        ("Boran the Adventurer", AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=2, reasoning="Armory upgrade")),
    ]

    for agent_name, dec in purchases:
        rec = execute_transaction(state, agent_name, dec)
        assert rec.status == "EXECUTED"

    # All three goods experienced positive net demand, prices rise
    for item_name, qty in [("Raw Gem", 5), ("Health Potion", 2), ("Iron Sword", 2)]:
        old_price = state.items[item_name].price
        new_price = calculate_new_price(old_price, net_demand=qty, k=0.05)
        assert new_price > old_price
        state.items[item_name].price = new_price

    assert_state_invariants(state)


# ============================================================================
# SCENARIO 5: Full Macroeconomic Stabilization Cycle
# ============================================================================

def test_scenario_full_macroeconomic_cycle(fresh_economy_state):
    """Full lifecycle: Baseline -> Dragon Attack -> Tax Relief -> Gold Rush -> Stable Convergence."""
    state = fresh_economy_state

    # Step 1: Baseline tick
    state.tick = 1
    assert_state_invariants(state)

    # Step 2: Dragon Attack strikes
    apply_dragon_attack(state)
    assert state.items["Health Potion"].price == 35.0
    assert state.items["Health Potion"].supply == 2

    # Step 3: Central Bank institutes 0% tax holiday to assist recovery
    state.tax_rate = 0.0

    # Step 4: Central Bank injects Gold Rush stimulus
    apply_gold_rush(state, gold_amount=100.0)

    # Step 5: Adventurer Boran uses stimulus to buy 1 scarce potion under zero tax
    potion_dec = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Stimulus potion buy")
    rec = execute_transaction(state, "Boran the Adventurer", potion_dec)
    assert rec.status == "EXECUTED"
    assert rec.tax_paid == 0.0
    assert rec.total_cost == 35.0
    assert state.items["Health Potion"].supply == 1

    # Step 6: Post-stimulus price adjustment
    state.items["Health Potion"].price = calculate_new_price(35.0, net_demand=1, k=0.05)
    assert state.items["Health Potion"].price == 36.75

    # Step 7: Restore standard tax rate of 10%
    state.tax_rate = 0.10
    state.tick = 2
    assert_state_invariants(state)
