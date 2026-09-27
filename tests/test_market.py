"""
Unit Test Suite for src/market.py (Milestone 1).

Tests:
1. Price discovery formula with positive, negative, and zero Delta D.
2. Price floor enforcement (never drops below 1.0 Gold, including extreme Delta D = -100).
3. Tax calculations across tax rates (0%, 10%, 50%, 80%) and zero/negative inputs.
4. BUY validation (exact gold, surplus gold, deficient gold, deficient market supply).
5. SELL validation (exact inventory, surplus inventory, deficient inventory).
6. Atomic state execution (successful trades mutate state, rejected trades preserve state).
7. Macroeconomic shocks (Dragon Attack and Gold Rush mutations).
"""

import pytest
from src.models import (
    ActionType,
    AgentDecision,
    AgentState,
    EconomyState,
    ItemState,
    TransactionRecord,
)
from src.market import (
    calculate_new_price,
    calculate_tax,
    validate_transaction,
    execute_transaction,
    calculate_net_demand,
    update_market_prices,
    apply_dragon_attack,
    apply_gold_rush,
    apply_trade_war,
    apply_market_crash,
    apply_black_market,
)


# ============================================================================
# 1. Price Discovery Formula Tests (calculate_new_price)
# ============================================================================

class TestPriceDiscovery:
    """Tests P_new = max(min_price, round(old_price * (1 + k * net_demand), 2))."""

    def test_price_discovery_zero_demand(self):
        """Zero net demand (Delta D = 0) must preserve original price."""
        assert calculate_new_price(old_price=20.0, net_demand=0, k=0.05) == 20.0
        assert calculate_new_price(old_price=1.0, net_demand=0, k=0.05) == 1.0
        assert calculate_new_price(old_price=35.5, net_demand=0, k=0.05) == 35.5
        assert calculate_new_price(old_price=100.0, net_demand=0, k=0.05) == 100.0

    @pytest.mark.parametrize(
        "old_price, net_demand, k, expected_price",
        [
            (20.0, 1, 0.05, 21.0),     # 20.0 * (1 + 0.05 * 1) = 21.0
            (20.0, 2, 0.05, 22.0),     # 20.0 * (1 + 0.05 * 2) = 22.0
            (20.0, 5, 0.05, 25.0),     # 20.0 * (1 + 0.05 * 5) = 25.0
            (30.0, 10, 0.05, 45.0),    # 30.0 * (1 + 0.05 * 10) = 45.0
            (15.0, 3, 0.05, 17.25),    # 15.0 * (1 + 0.15) = 17.25
            (10.0, 4, 0.10, 14.0),     # Custom k = 0.10
        ],
    )
    def test_price_discovery_positive_demand(self, old_price, net_demand, k, expected_price):
        """Positive net demand increases price deterministically."""
        assert calculate_new_price(old_price, net_demand, k=k) == expected_price

    @pytest.mark.parametrize(
        "old_price, net_demand, k, expected_price",
        [
            (20.0, -1, 0.05, 19.0),    # 20.0 * (1 - 0.05) = 19.0
            (20.0, -2, 0.05, 18.0),    # 20.0 * (1 - 0.10) = 18.0
            (20.0, -5, 0.05, 15.0),    # 20.0 * (1 - 0.25) = 15.0
            (30.0, -10, 0.05, 15.0),   # 30.0 * (1 - 0.50) = 15.0
            (15.0, -4, 0.05, 12.0),    # 15.0 * (1 - 0.20) = 12.0
        ],
    )
    def test_price_discovery_negative_demand(self, old_price, net_demand, k, expected_price):
        """Negative net demand decreases price deterministically."""
        assert calculate_new_price(old_price, net_demand, k=k) == expected_price

    def test_price_floor_enforcement_at_multiplier_zero(self):
        """Delta D = -20 yields multiplier (1 + 0.05 * -20) = 0.0 -> clamped to 1.0."""
        assert calculate_new_price(old_price=20.0, net_demand=-20, k=0.05) == 1.0

    def test_price_floor_enforcement_at_negative_multiplier(self):
        """Delta D = -25 yields negative raw price -> clamped to 1.0."""
        assert calculate_new_price(old_price=20.0, net_demand=-25, k=0.05) == 1.0

    def test_price_floor_extreme_negative_demand(self):
        """Massive sell volume (Delta D = -100) must strictly clamp to 1.0 Gold."""
        assert calculate_new_price(old_price=100.0, net_demand=-100, k=0.05) == 1.0
        assert calculate_new_price(old_price=500.0, net_demand=-1000, k=0.05) == 1.0

    def test_price_floor_already_at_minimum(self):
        """Item already at 1.0 Gold with sell pressure remains pinned at 1.0 Gold."""
        assert calculate_new_price(old_price=1.0, net_demand=-5, k=0.05) == 1.0
        assert calculate_new_price(old_price=1.0, net_demand=-100, k=0.05) == 1.0

    def test_price_floor_custom_bound(self):
        """Custom price floor (e.g. min_price = 5.0) is respected."""
        assert calculate_new_price(old_price=20.0, net_demand=-50, min_price=5.0) == 5.0

    def test_price_rounding_precision(self):
        """Result must round to 2 decimal places."""
        # 13.33 * (1 + 0.05 * 1) = 13.9965 -> 14.00
        assert calculate_new_price(old_price=13.33, net_demand=1, k=0.05) == 14.00


# ============================================================================
# 2. Tax Calculation Tests (calculate_tax)
# ============================================================================

class TestTaxCalculation:
    """Tests T = round(unit_price * quantity * tax_rate, 2)."""

    def test_tax_rate_zero_percent(self):
        """At 0% tax, no tax is charged regardless of quantity or price."""
        assert calculate_tax(unit_price=20.0, quantity=1, tax_rate=0.0) == 0.0
        assert calculate_tax(unit_price=100.0, quantity=10, tax_rate=0.0) == 0.0

    def test_tax_rate_ten_percent(self):
        """At default 10% tax, T = round(price * quantity * 0.10, 2)."""
        assert calculate_tax(unit_price=20.0, quantity=1, tax_rate=0.10) == 2.0
        assert calculate_tax(unit_price=20.0, quantity=3, tax_rate=0.10) == 6.0
        assert calculate_tax(unit_price=35.0, quantity=2, tax_rate=0.10) == 7.0

    def test_tax_rate_fifty_percent(self):
        """At 50% tax, tax is exactly half the total unit cost."""
        assert calculate_tax(unit_price=20.0, quantity=1, tax_rate=0.50) == 10.0
        assert calculate_tax(unit_price=35.0, quantity=2, tax_rate=0.50) == 35.0

    def test_tax_rate_eighty_percent(self):
        """At 80% maximum legal tax, T = round(price * quantity * 0.80, 2)."""
        assert calculate_tax(unit_price=20.0, quantity=1, tax_rate=0.80) == 16.0
        assert calculate_tax(unit_price=10.0, quantity=5, tax_rate=0.80) == 40.0

    def test_tax_fractional_rounding(self):
        """Tax with fractional rounding precision."""
        tax = calculate_tax(unit_price=15.25, quantity=1, tax_rate=0.10)
        assert tax in (1.52, 1.53)

    def test_tax_zero_or_negative_guards(self):
        """Non-positive quantities or prices return 0.0 tax."""
        assert calculate_tax(unit_price=20.0, quantity=0, tax_rate=0.10) == 0.0
        assert calculate_tax(unit_price=-20.0, quantity=1, tax_rate=0.10) == 0.0
        assert calculate_tax(unit_price=20.0, quantity=1, tax_rate=-0.10) == 0.0


# ============================================================================
# 3. Transaction Validation Tests (validate_transaction)
# ============================================================================

class TestTransactionValidation:
    """Tests buyer gold, seller inventory, and market supply constraint checks."""

    @pytest.fixture
    def sample_item(self):
        return ItemState(name="Health Potion", price=20.0, supply=10)

    @pytest.fixture
    def sample_agent(self):
        return AgentState(
            name="TestAgent",
            persona="Tester",
            gold=100.0,
            inventory={"Health Potion": 3, "Iron Sword": 1},
        )

    # --- BUY Validation ---

    def test_buy_validation_exact_gold(self, sample_item):
        """BUY with agent gold exactly equal to unit_price * quantity + tax."""
        agent = AgentState(name="ExactBuyer", persona="Buyer", gold=22.0, inventory={})
        valid, msg = validate_transaction(agent, sample_item, ActionType.BUY, quantity=1, tax_rate=0.10)
        assert valid is True
        assert "valid" in msg.lower()

    def test_buy_validation_surplus_gold(self, sample_item, sample_agent):
        """BUY with surplus gold succeeds."""
        valid, msg = validate_transaction(sample_agent, sample_item, ActionType.BUY, quantity=1, tax_rate=0.10)
        assert valid is True

    def test_buy_validation_deficient_gold(self, sample_item):
        """BUY with deficient gold (even by 0.01) must fail."""
        agent = AgentState(name="PoorBuyer", persona="Buyer", gold=21.99, inventory={})
        valid, msg = validate_transaction(agent, sample_item, ActionType.BUY, quantity=1, tax_rate=0.10)
        assert valid is False
        assert "insufficient gold" in msg.lower()

    def test_buy_validation_insufficient_market_supply(self, sample_agent):
        """BUY when market supply is lower than requested quantity must fail."""
        scarce_item = ItemState(name="Health Potion", price=20.0, supply=2)
        valid, msg = validate_transaction(sample_agent, scarce_item, ActionType.BUY, quantity=5, tax_rate=0.10)
        assert valid is False
        assert "insufficient market supply" in msg.lower()

    def test_buy_validation_exact_market_supply(self, sample_agent):
        """BUY when market supply exactly matches quantity succeeds."""
        scarce_item = ItemState(name="Health Potion", price=20.0, supply=2)
        valid, msg = validate_transaction(sample_agent, scarce_item, ActionType.BUY, quantity=2, tax_rate=0.10)
        assert valid is True

    def test_buy_validation_missing_item(self, sample_agent):
        """BUY with item=None must fail validation."""
        valid, msg = validate_transaction(sample_agent, None, ActionType.BUY, quantity=1, tax_rate=0.10)
        assert valid is False
        assert "requires a valid item" in msg.lower() or "item" in msg.lower()

    # --- SELL Validation ---

    def test_sell_validation_exact_inventory(self, sample_item, sample_agent):
        """SELL with agent inventory exactly equal to requested quantity succeeds."""
        valid, msg = validate_transaction(sample_agent, sample_item, ActionType.SELL, quantity=3, tax_rate=0.10)
        assert valid is True

    def test_sell_validation_surplus_inventory(self, sample_item, sample_agent):
        """SELL with agent holding more inventory than requested quantity succeeds."""
        valid, msg = validate_transaction(sample_agent, sample_item, ActionType.SELL, quantity=1, tax_rate=0.10)
        assert valid is True

    def test_sell_validation_deficient_inventory(self, sample_item, sample_agent):
        """SELL when agent inventory is less than quantity must fail."""
        valid, msg = validate_transaction(sample_agent, sample_item, ActionType.SELL, quantity=4, tax_rate=0.10)
        assert valid is False
        assert "insufficient inventory" in msg.lower()

    def test_sell_validation_zero_inventory(self, sample_agent):
        """SELL when agent owns 0 units of item must fail."""
        gem = ItemState(name="Raw Gem", price=15.0, supply=50)
        valid, msg = validate_transaction(sample_agent, gem, ActionType.SELL, quantity=1, tax_rate=0.10)
        assert valid is False
        assert "insufficient inventory" in msg.lower()

    # --- HOLD and CRAFT Validation ---

    def test_hold_validation_always_valid(self, sample_agent):
        """HOLD is always valid and does not require item or supply."""
        valid, msg = validate_transaction(sample_agent, None, ActionType.HOLD, quantity=1, tax_rate=0.10)
        assert valid is True

    def test_craft_validation_falls_back_to_hold(self, sample_agent):
        """CRAFT is valid in Phase 1 as a no-op fallback."""
        valid, msg = validate_transaction(sample_agent, None, ActionType.CRAFT, quantity=1, tax_rate=0.10)
        assert valid is True


# ============================================================================
# 4. Atomic State Execution Tests (execute_transaction)
# ============================================================================

class TestAtomicExecution:
    """Tests atomic execution: successful mutations vs untouched state on rejection."""

    @pytest.fixture
    def initial_state(self):
        return EconomyState(
            tick=1,
            running=True,
            tax_rate=0.10,
            items={
                "Health Potion": ItemState(name="Health Potion", price=20.0, supply=50),
                "Iron Sword": ItemState(name="Iron Sword", price=30.0, supply=20),
            },
            agents={
                "Garrick": AgentState(
                    name="Garrick",
                    persona="Garrick the Greedy",
                    gold=150.0,
                    inventory={"Health Potion": 2, "Iron Sword": 1},
                ),
                "Boran": AgentState(
                    name="Boran",
                    persona="Boran the Adventurer",
                    gold=10.0,
                    inventory={"Health Potion": 0},
                ),
            },
            recent_transactions=[],
        )

    def test_atomic_buy_success(self, initial_state):
        """Successful BUY: gold debited, inventory credited, market supply debited."""
        decision = AgentDecision(
            action=ActionType.BUY,
            item="Health Potion",
            quantity=2,
            reasoning="Buying 2 potions for safety",
        )
        record = execute_transaction(initial_state, "Garrick", decision)

        assert record.status == "EXECUTED"
        assert record.total_cost == 44.0
        assert record.tax_paid == 4.0
        assert initial_state.agents["Garrick"].gold == 106.0  # 150.0 - 44.0
        assert initial_state.agents["Garrick"].inventory["Health Potion"] == 4  # 2 + 2
        assert initial_state.items["Health Potion"].supply == 48  # 50 - 2
        assert len(initial_state.recent_transactions) == 1

    def test_atomic_buy_rejected_insufficient_gold(self, initial_state):
        """Rejected BUY: state remains completely pristine, no partial changes."""
        decision = AgentDecision(
            action=ActionType.BUY,
            item="Health Potion",
            quantity=1,
            reasoning="Need potion but broke",
        )
        record = execute_transaction(initial_state, "Boran", decision)

        assert record.status == "REJECTED"
        assert "insufficient gold" in record.reason.lower()
        # Invariants: gold, inventory, and market supply unchanged
        assert initial_state.agents["Boran"].gold == 10.0
        assert initial_state.agents["Boran"].inventory["Health Potion"] == 0
        assert initial_state.items["Health Potion"].supply == 50
        assert len(initial_state.recent_transactions) == 1

    def test_atomic_sell_success(self, initial_state):
        """Successful SELL: inventory debited, gold credited, market supply credited."""
        decision = AgentDecision(
            action=ActionType.SELL,
            item="Iron Sword",
            quantity=1,
            reasoning="Selling sword for profit",
        )
        record = execute_transaction(initial_state, "Garrick", decision)

        assert record.status == "EXECUTED"
        assert record.total_cost == 30.0
        assert record.tax_paid == 3.0
        assert initial_state.agents["Garrick"].gold == 177.0  # 150.0 + 27.0 (30.0 - 3.0 tax)
        assert initial_state.agents["Garrick"].inventory["Iron Sword"] == 0  # 1 - 1
        assert initial_state.items["Iron Sword"].supply == 21  # 20 + 1

    def test_atomic_sell_rejected_insufficient_inventory(self, initial_state):
        """Rejected SELL: state remains pristine, no gold credited."""
        decision = AgentDecision(
            action=ActionType.SELL,
            item="Health Potion",
            quantity=1,
            reasoning="Selling potion I do not have",
        )
        record = execute_transaction(initial_state, "Boran", decision)

        assert record.status == "REJECTED"
        assert "insufficient inventory" in record.reason.lower()
        assert initial_state.agents["Boran"].gold == 10.0
        assert initial_state.agents["Boran"].inventory["Health Potion"] == 0
        assert initial_state.items["Health Potion"].supply == 50

    def test_atomic_hold_execution(self, initial_state):
        """HOLD action creates EXECUTED record with zero financial impact."""
        decision = AgentDecision(
            action=ActionType.HOLD,
            item=None,
            quantity=1,
            reasoning="Market conditions unfavorable",
        )
        record = execute_transaction(initial_state, "Garrick", decision)

        assert record.status == "EXECUTED"
        assert record.total_cost == 0.0
        assert record.tax_paid == 0.0
        assert initial_state.agents["Garrick"].gold == 150.0

    def test_atomic_unknown_agent_rejection(self, initial_state):
        """Transaction by unknown agent is rejected without modifying store."""
        decision = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Ghost agent")
        record = execute_transaction(initial_state, "NonExistentAgent", decision)

        assert record.status == "REJECTED"
        assert "does not exist" in record.reason.lower()

    def test_atomic_unknown_item_rejection(self, initial_state):
        """Transaction for non-catalog item is rejected cleanly."""
        decision = AgentDecision(
            action=ActionType.BUY,
            item="Health Potion",
            quantity=1,
            reasoning="Magic wand",
        )
        decision.item = "Uncataloged Item"
        record = execute_transaction(initial_state, "Garrick", decision)

        assert record.status == "REJECTED"
        assert "not found" in record.reason.lower()


# ============================================================================
# 5. Net Demand & Tick Market Price Updates
# ============================================================================

class TestNetDemandAndPriceUpdates:
    """Tests net demand calculation and multi-item tick price adjustment."""

    def test_net_demand_calculation(self):
        """Delta D sums executed BUY quantities minus executed SELL quantities."""
        records = [
            TransactionRecord(
                tick=1, agent_name="A", action=ActionType.BUY, item="Health Potion",
                quantity=3, unit_price=20.0, tax_paid=6.0, total_cost=66.0, status="EXECUTED"
            ),
            TransactionRecord(
                tick=1, agent_name="B", action=ActionType.SELL, item="Health Potion",
                quantity=1, unit_price=20.0, tax_paid=0.0, total_cost=20.0, status="EXECUTED"
            ),
            TransactionRecord(
                tick=1, agent_name="C", action=ActionType.BUY, item="Health Potion",
                quantity=5, unit_price=20.0, tax_paid=10.0, total_cost=110.0, status="REJECTED"
            ),
        ]
        delta_d = calculate_net_demand(records, "Health Potion")
        assert delta_d == 2  # 3 - 1 = 2 (rejected 5 is ignored)

    def test_update_market_prices(self):
        """update_market_prices updates state.items deterministically."""
        state = EconomyState(
            tick=1,
            running=True,
            tax_rate=0.10,
            items={
                "Health Potion": ItemState(name="Health Potion", price=20.0, supply=50),
                "Iron Sword": ItemState(name="Iron Sword", price=30.0, supply=20),
            },
            agents={},
        )
        transactions = [
            TransactionRecord(
                tick=1, agent_name="A", action=ActionType.BUY, item="Health Potion",
                quantity=2, unit_price=20.0, tax_paid=4.0, total_cost=44.0, status="EXECUTED"
            ),
            TransactionRecord(
                tick=1, agent_name="B", action=ActionType.SELL, item="Iron Sword",
                quantity=4, unit_price=30.0, tax_paid=0.0, total_cost=120.0, status="EXECUTED"
            ),
        ]
        new_prices = update_market_prices(state, transactions, k=0.05)
        # Health Potion: Delta D = +2 -> 20.0 * 1.10 = 22.0
        assert new_prices["Health Potion"] == 22.0
        assert state.items["Health Potion"].price == 22.0
        # Iron Sword: Delta D = -4 -> 30.0 * 0.80 = 24.0
        assert new_prices["Iron Sword"] == 24.0
        assert state.items["Iron Sword"].price == 24.0


# ============================================================================
# 6. Policy Shocks Tests (apply_dragon_attack, apply_gold_rush)
# ============================================================================

class TestMacroeconomicShocks:
    """Tests Dragon Attack and Gold Rush shock events."""

    @pytest.fixture
    def state_with_agents_and_items(self):
        return EconomyState(
            tick=5,
            running=True,
            tax_rate=0.10,
            items={
                "Health Potion": ItemState(name="Health Potion", price=20.0, supply=100),
                "Iron Sword": ItemState(name="Iron Sword", price=30.0, supply=50),
                "Raw Gem": ItemState(name="Raw Gem", price=15.0, supply=80),
            },
            agents={
                "Garrick": AgentState(name="Garrick", persona="Greedy", gold=150.0, inventory={}),
                "Cora": AgentState(name="Cora", persona="Farmer", gold=60.0, inventory={}),
                "Boran": AgentState(name="Boran", persona="Adventurer", gold=40.0, inventory={}),
            },
        )

    def test_apply_dragon_attack(self, state_with_agents_and_items):
        """Dragon Attack sets Health Potion supply = 2 and base price = 35.0 Gold."""
        apply_dragon_attack(state_with_agents_and_items)

        # Health Potion mutated
        assert state_with_agents_and_items.items["Health Potion"].supply == 2
        assert state_with_agents_and_items.items["Health Potion"].price == 35.0

        # Invariants: other commodities untouched
        assert state_with_agents_and_items.items["Iron Sword"].supply == 50
        assert state_with_agents_and_items.items["Iron Sword"].price == 30.0
        assert state_with_agents_and_items.items["Raw Gem"].supply == 80
        assert state_with_agents_and_items.items["Raw Gem"].price == 15.0

        # Agent balances untouched
        assert state_with_agents_and_items.agents["Garrick"].gold == 150.0
        assert state_with_agents_and_items.agents["Cora"].gold == 60.0
        assert state_with_agents_and_items.agents["Boran"].gold == 40.0

    def test_apply_dragon_attack_idempotent(self, state_with_agents_and_items):
        """Subsequent Dragon Attack calls deterministically overwrite to 2 supply and 35.0 price."""
        state_with_agents_and_items.items["Health Potion"].supply = 0
        state_with_agents_and_items.items["Health Potion"].price = 55.0
        apply_dragon_attack(state_with_agents_and_items)
        assert state_with_agents_and_items.items["Health Potion"].supply == 2
        assert state_with_agents_and_items.items["Health Potion"].price == 35.0

    def test_apply_gold_rush_default(self, state_with_agents_and_items):
        """Gold Rush credits +100.0 Gold to each agent."""
        apply_gold_rush(state_with_agents_and_items)

        assert state_with_agents_and_items.agents["Garrick"].gold == 250.0  # 150 + 100
        assert state_with_agents_and_items.agents["Cora"].gold == 160.0     # 60 + 100
        assert state_with_agents_and_items.agents["Boran"].gold == 140.0    # 40 + 100

        # Invariants: market items untouched
        assert state_with_agents_and_items.items["Health Potion"].supply == 100
        assert state_with_agents_and_items.items["Health Potion"].price == 20.0

    def test_apply_gold_rush_custom_amount(self, state_with_agents_and_items):
        """Gold Rush credits custom amount (e.g. +50.0 Gold)."""
        apply_gold_rush(state_with_agents_and_items, gold_amount=50.0)

        assert state_with_agents_and_items.agents["Garrick"].gold == 200.0
        assert state_with_agents_and_items.agents["Cora"].gold == 110.0
        assert state_with_agents_and_items.agents["Boran"].gold == 90.0

    def test_apply_trade_war(self, state_with_agents_and_items):
        """Trade War sets tax rate to 0.50 (50%)."""
        apply_trade_war(state_with_agents_and_items)
        assert state_with_agents_and_items.tax_rate == 0.50

    def test_apply_market_crash(self, state_with_agents_and_items):
        """Market Crash reduces all prices by 40% with minimum floor 1.0."""
        apply_market_crash(state_with_agents_and_items)
        assert state_with_agents_and_items.items["Health Potion"].price == 12.0  # 20.0 * 0.60
        assert state_with_agents_and_items.items["Iron Sword"].price == 18.0     # 30.0 * 0.60
        assert state_with_agents_and_items.items["Raw Gem"].price == 9.0         # 15.0 * 0.60

    def test_apply_black_market(self, state_with_agents_and_items):
        """Black Market spikes prices by 25% and gives +150G to one agent."""
        initial_total_gold = sum(a.gold for a in state_with_agents_and_items.agents.values())
        apply_black_market(state_with_agents_and_items)
        assert state_with_agents_and_items.items["Health Potion"].price == 25.0  # 20.0 * 1.25
        assert state_with_agents_and_items.items["Iron Sword"].price == 37.5     # 30.0 * 1.25
        assert state_with_agents_and_items.items["Raw Gem"].price == 18.75       # 15.0 * 1.25
        new_total_gold = sum(a.gold for a in state_with_agents_and_items.agents.values())
        assert round(new_total_gold - initial_total_gold, 2) == 150.0

