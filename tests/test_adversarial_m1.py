"""
Adversarial Stress Verification Test Suite for Milestone 1 (M1).

Designed and executed by teamwork_preview_challenger (m1_challenger_1).

Covers:
1. Extreme mathematical limits: massive sell pressure (Delta D = -10^6), extreme buy pressure (Delta D = 10^6),
   fractional price fluctuations, and zero demand invariance.
2. Tax calculation stability across extreme tax rates (0.0, 0.80, fractional float rates like 0.33333).
3. State atomicity under rejected BUY/SELL combinations (ensuring 0 state corruption).
4. Dragon Attack and Gold Rush shocks under boundary conditions.
"""

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
    calculate_net_demand,
    update_market_prices,
    apply_dragon_attack,
    apply_gold_rush,
)
from tests.conftest import assert_state_invariants


# ============================================================================
# 1. EXTREME MATHEMATICAL LIMITS
# ============================================================================

class TestAdversarialExtremeMath:
    """Stress tests extreme numerical regimes of price discovery formula."""

    def test_extreme_sell_pressure_minus_one_million(self):
        """Massive sell pressure (Delta D = -1,000,000) must strictly clamp to 1.0 Gold."""
        # Baseline starting prices
        assert calculate_new_price(old_price=20.0, net_demand=-1_000_000, k=0.05) == 1.0
        assert calculate_new_price(old_price=100.0, net_demand=-1_000_000, k=0.05) == 1.0
        assert calculate_new_price(old_price=1.0, net_demand=-1_000_000, k=0.05) == 1.0
        assert calculate_new_price(old_price=10_000.0, net_demand=-1_000_000, k=0.05) == 1.0

    def test_extreme_sell_pressure_custom_floor(self):
        """Massive sell pressure clamps to arbitrary min_price."""
        assert calculate_new_price(old_price=50.0, net_demand=-1_000_000, k=0.05, min_price=7.50) == 7.50
        assert calculate_new_price(old_price=1.0, net_demand=-1_000_000, k=0.05, min_price=0.25) == 0.25

    def test_extreme_buy_pressure_plus_one_million(self):
        """Massive buy pressure (Delta D = +1,000,000) scales deterministically without overflow."""
        # 20.0 * (1 + 0.05 * 1,000,000) = 20.0 * (1 + 50,000) = 20.0 * 50,001 = 1,000,020.0
        p1 = calculate_new_price(old_price=20.0, net_demand=1_000_000, k=0.05)
        assert p1 == 1_000_020.0

        # 1.0 * (1 + 0.05 * 1,000,000) = 50,001.0
        p2 = calculate_new_price(old_price=1.0, net_demand=1_000_000, k=0.05)
        assert p2 == 50_001.0

        # 15.0 * (1 + 0.05 * 1,000,000) = 15.0 * 50,001 = 750,015.0
        p3 = calculate_new_price(old_price=15.0, net_demand=1_000_000, k=0.05)
        assert p3 == 750_015.0

    def test_fractional_price_fluctuations_rounding(self):
        """Fractional prices with minor demand adjustments round cleanly to 2 decimals."""
        # 20.01 * (1 + 0.05 * 1) = 21.0105 -> round to 21.01
        assert calculate_new_price(old_price=20.01, net_demand=1, k=0.05) == 21.01

        # 20.05 * (1 + 0.05 * 1) = 21.0525 -> round to 21.05
        assert calculate_new_price(old_price=20.05, net_demand=1, k=0.05) == 21.05

        # 10.33 * (1 + 0.05 * -1) = 9.8135 -> round to 9.81
        assert calculate_new_price(old_price=10.33, net_demand=-1, k=0.05) == 9.81

        # 17.85 * (1 + 0.05 * 3) = 17.85 * 1.15 = 20.5275 -> round to 20.53
        assert calculate_new_price(old_price=17.85, net_demand=3, k=0.05) == 20.53

        # Precision guarantee: always matches 2-decimal representation
        p = calculate_new_price(old_price=33.33, net_demand=7, k=0.05)
        assert round(p, 2) == p

    def test_zero_demand_invariance(self):
        """Delta D = 0 preserves price across standard, floor, and fractional values."""
        assert calculate_new_price(old_price=20.0, net_demand=0, k=0.05) == 20.0
        assert calculate_new_price(old_price=1.0, net_demand=0, k=0.05) == 1.0
        assert calculate_new_price(old_price=17.85, net_demand=0, k=0.05) == 17.85
        assert calculate_new_price(old_price=999.99, net_demand=0, k=0.05) == 999.99

    def test_multi_tick_zero_demand_drift_freedom(self):
        """Iterative zero-demand steps over 100 ticks suffer 0.0 floating drift."""
        current_price = 17.85
        for _ in range(100):
            current_price = calculate_new_price(old_price=current_price, net_demand=0, k=0.05)
        assert current_price == 17.85


# ============================================================================
# 2. TAX CALCULATION STABILITY ACROSS EXTREME TAX RATES
# ============================================================================

class TestAdversarialTaxStability:
    """Stress tests transaction tax calculations across boundary and fractional rates."""

    def test_tax_rate_zero_absolute_boundary(self):
        """Tax rate 0.0 results in 0.0 tax across single, batch, and large transactions."""
        assert calculate_tax(unit_price=20.0, quantity=1, tax_rate=0.0) == 0.0
        assert calculate_tax(unit_price=100.0, quantity=10, tax_rate=0.0) == 0.0
        assert calculate_tax(unit_price=1.0, quantity=1, tax_rate=0.0) == 0.0
        assert calculate_tax(unit_price=1_000_000.0, quantity=10, tax_rate=0.0) == 0.0

    def test_tax_rate_eighty_percent_macroeconomic_ceiling(self):
        """Tax rate 0.80 calculates 80% tax accurately and rounded to 2 decimals."""
        # 20.0 * 1 * 0.80 = 16.0
        assert calculate_tax(unit_price=20.0, quantity=1, tax_rate=0.80) == 16.0
        # 1.0 * 1 * 0.80 = 0.80
        assert calculate_tax(unit_price=1.0, quantity=1, tax_rate=0.80) == 0.80
        # 35.0 * 10 * 0.80 = 280.0
        assert calculate_tax(unit_price=35.0, quantity=10, tax_rate=0.80) == 280.0
        # 17.85 * 3 * 0.80 = 42.84
        assert calculate_tax(unit_price=17.85, quantity=3, tax_rate=0.80) == 42.84

    def test_tax_rate_fractional_repeating_third(self):
        """Fractional repeating tax rate like 0.33333 rounds cleanly to cents."""
        # 20.0 * 1 * 0.33333 = 6.6666 -> 6.67
        assert calculate_tax(unit_price=20.0, quantity=1, tax_rate=0.33333) == 6.67
        # 30.0 * 1 * (1.0 / 3.0) = 10.0
        assert calculate_tax(unit_price=30.0, quantity=1, tax_rate=1.0 / 3.0) == 10.0
        # 10.0 * 7 * 0.33333 = 23.3331 -> 23.33
        assert calculate_tax(unit_price=10.0, quantity=7, tax_rate=0.33333) == 23.33

    def test_tax_rate_arbitrary_fractional_floats(self):
        """Arbitrary 6-decimal fractional tax rates round cleanly."""
        # 15.0 * 2 * 0.123456 = 3.70368 -> 3.70
        assert calculate_tax(unit_price=15.0, quantity=2, tax_rate=0.123456) == 3.70
        # 9.99 * 5 * 0.0777 = 49.95 * 0.0777 = 3.881115 -> 3.88
        assert calculate_tax(unit_price=9.99, quantity=5, tax_rate=0.0777) == 3.88

    def test_tax_invalid_and_negative_inputs(self):
        """Negative and non-positive parameters yield 0.0 tax without throwing."""
        assert calculate_tax(unit_price=-20.0, quantity=1, tax_rate=0.10) == 0.0
        assert calculate_tax(unit_price=20.0, quantity=-2, tax_rate=0.10) == 0.0
        assert calculate_tax(unit_price=20.0, quantity=0, tax_rate=0.10) == 0.0
        assert calculate_tax(unit_price=20.0, quantity=1, tax_rate=-0.10) == 0.0
        assert calculate_tax(unit_price=0.0, quantity=5, tax_rate=0.10) == 0.0

    def test_tax_extreme_magnitude_scaling(self):
        """Very large price, max quantity (10), and max tax (0.80) scale cleanly."""
        # 1,000,000.0 * 10 * 0.80 = 8,000,000.0
        assert calculate_tax(unit_price=1_000_000.0, quantity=10, tax_rate=0.80) == 8_000_000.0


# ============================================================================
# 3. STATE ATOMICITY UNDER REJECTED BUY/SELL COMBINATIONS
# ============================================================================

class TestAdversarialStateAtomicity:
    """Stress tests state preservation and 0 state corruption under rejections."""

    @pytest.fixture
    def isolated_economy(self):
        return EconomyState(
            tick=1,
            running=True,
            tax_rate=0.10,
            items={
                "Health Potion": ItemState(name="Health Potion", price=20.0, supply=10),
                "Iron Sword": ItemState(name="Iron Sword", price=30.0, supply=10),
                "Raw Gem": ItemState(name="Raw Gem", price=15.0, supply=10),
            },
            agents={
                "Garrick": AgentState(
                    name="Garrick",
                    persona="Garrick the Greedy",
                    gold=100.0,
                    inventory={"Health Potion": 2, "Iron Sword": 1, "Raw Gem": 0},
                ),
                "PoorAgent": AgentState(
                    name="PoorAgent",
                    persona="Poor Agent",
                    gold=21.99,  # 0.01 Gold short for 20.0 + 2.0 tax
                    inventory={"Health Potion": 0, "Iron Sword": 0, "Raw Gem": 0},
                ),
            },
            recent_transactions=[],
        )

    def test_atomicity_buy_sub_cent_deficit_rejection(self, isolated_economy):
        """BUY rejected due to 0.01 Gold deficit leaves state 100% uncorrupted."""
        decision = AgentDecision(
            action=ActionType.BUY,
            item="Health Potion",
            quantity=1,
            reasoning="Attempting buy with 0.01 gold deficit",
        )
        record = execute_transaction(isolated_economy, "PoorAgent", decision)

        assert record.status == "REJECTED"
        assert "insufficient gold" in record.reason.lower()
        # Invariants: PoorAgent gold remains exactly 21.99
        assert isolated_economy.agents["PoorAgent"].gold == 21.99
        assert isolated_economy.agents["PoorAgent"].inventory["Health Potion"] == 0
        assert isolated_economy.items["Health Potion"].supply == 10
        assert isolated_economy.items["Health Potion"].price == 20.0
        assert_state_invariants(isolated_economy)

    def test_atomicity_buy_excessive_quantity_market_supply(self, isolated_economy):
        """BUY rejected due to insufficient market supply leaves state uncorrupted."""
        decision = AgentDecision(
            action=ActionType.BUY,
            item="Health Potion",
            quantity=10,  # Supply is 10, but let's test supply=5
            reasoning="Buy all potions",
        )
        isolated_economy.items["Health Potion"].supply = 5
        record = execute_transaction(isolated_economy, "Garrick", decision)

        assert record.status == "REJECTED"
        assert "insufficient market supply" in record.reason.lower()
        assert isolated_economy.agents["Garrick"].gold == 100.0
        assert isolated_economy.agents["Garrick"].inventory["Health Potion"] == 2
        assert isolated_economy.items["Health Potion"].supply == 5
        assert_state_invariants(isolated_economy)

    def test_atomicity_sell_zero_inventory_rejection(self, isolated_economy):
        """SELL rejected due to zero inventory leaves balances and supplies uncorrupted."""
        decision = AgentDecision(
            action=ActionType.SELL,
            item="Raw Gem",
            quantity=1,
            reasoning="Selling raw gem I do not possess",
        )
        record = execute_transaction(isolated_economy, "Garrick", decision)

        assert record.status == "REJECTED"
        assert "insufficient inventory" in record.reason.lower()
        assert isolated_economy.agents["Garrick"].gold == 100.0
        assert isolated_economy.agents["Garrick"].inventory["Raw Gem"] == 0
        assert isolated_economy.items["Raw Gem"].supply == 10
        assert_state_invariants(isolated_economy)

    def test_atomicity_sell_partial_inventory_deficit(self, isolated_economy):
        """SELL rejected when holding 2 units but attempting to sell 3."""
        decision = AgentDecision(
            action=ActionType.SELL,
            item="Health Potion",
            quantity=3,
            reasoning="Over-selling inventory",
        )
        record = execute_transaction(isolated_economy, "Garrick", decision)

        assert record.status == "REJECTED"
        assert isolated_economy.agents["Garrick"].gold == 100.0
        assert isolated_economy.agents["Garrick"].inventory["Health Potion"] == 2
        assert isolated_economy.items["Health Potion"].supply == 10
        assert_state_invariants(isolated_economy)

    def test_atomicity_nonexistent_agent_rejection(self, isolated_economy):
        """Transaction by phantom agent mutates 0 agents and 0 items."""
        decision = AgentDecision(
            action=ActionType.BUY,
            item="Health Potion",
            quantity=1,
            reasoning="Phantom order",
        )
        record = execute_transaction(isolated_economy, "PhantomGhost", decision)

        assert record.status == "REJECTED"
        assert "does not exist" in record.reason.lower()
        assert isolated_economy.items["Health Potion"].supply == 10
        assert_state_invariants(isolated_economy)

    def test_atomicity_nonexistent_item_rejection(self, isolated_economy):
        """Transaction for item not in catalog mutates 0 agent balances."""
        decision = AgentDecision(
            action=ActionType.BUY,
            item="Health Potion",
            quantity=1,
            reasoning="Secret item",
        )
        decision.item = "Mythic Bow"
        record = execute_transaction(isolated_economy, "Garrick", decision)

        assert record.status == "REJECTED"
        assert "not found" in record.reason.lower()
        assert isolated_economy.agents["Garrick"].gold == 100.0
        assert_state_invariants(isolated_economy)

    def test_net_demand_completely_ignores_rejected_transactions(self):
        """calculate_net_demand strictly filters out all REJECTED transactions."""
        records = [
            # 5 rejected BUY orders totaling 25 units
            TransactionRecord(
                tick=1, agent_name="P1", action=ActionType.BUY, item="Health Potion",
                quantity=5, unit_price=20.0, tax_paid=0.0, total_cost=0.0, status="REJECTED"
            ),
            TransactionRecord(
                tick=1, agent_name="P2", action=ActionType.BUY, item="Health Potion",
                quantity=20, unit_price=20.0, tax_paid=0.0, total_cost=0.0, status="REJECTED"
            ),
            # 5 rejected SELL orders totaling 15 units
            TransactionRecord(
                tick=1, agent_name="P3", action=ActionType.SELL, item="Health Potion",
                quantity=15, unit_price=20.0, tax_paid=0.0, total_cost=0.0, status="REJECTED"
            ),
            # 1 EXECUTED BUY of 2 units
            TransactionRecord(
                tick=1, agent_name="E1", action=ActionType.BUY, item="Health Potion",
                quantity=2, unit_price=20.0, tax_paid=4.0, total_cost=44.0, status="EXECUTED"
            ),
            # 1 EXECUTED SELL of 1 unit
            TransactionRecord(
                tick=1, agent_name="E2", action=ActionType.SELL, item="Health Potion",
                quantity=1, unit_price=20.0, tax_paid=0.0, total_cost=20.0, status="EXECUTED"
            ),
        ]
        # Net demand should strictly be 2 - 1 = 1
        delta_d = calculate_net_demand(records, "Health Potion")
        assert delta_d == 1

    def test_update_market_prices_zero_corruption_when_all_rejected(self, isolated_economy):
        """When 100% of transactions in a tick are rejected, prices remain 100% invariant."""
        rejected_records = [
            TransactionRecord(
                tick=1, agent_name="P1", action=ActionType.BUY, item="Health Potion",
                quantity=5, unit_price=20.0, tax_paid=0.0, total_cost=0.0, status="REJECTED"
            ),
            TransactionRecord(
                tick=1, agent_name="P2", action=ActionType.SELL, item="Iron Sword",
                quantity=3, unit_price=30.0, tax_paid=0.0, total_cost=0.0, status="REJECTED"
            ),
        ]
        prices = update_market_prices(isolated_economy, rejected_records, k=0.05)
        assert prices["Health Potion"] == 20.0
        assert prices["Iron Sword"] == 30.0
        assert prices["Raw Gem"] == 15.0


# ============================================================================
# 4. DRAGON ATTACK AND GOLD RUSH SHOCKS UNDER BOUNDARY CONDITIONS
# ============================================================================

class TestAdversarialMacroeconomicShocks:
    """Stress tests shock events under extreme boundary states."""

    @pytest.fixture
    def extreme_economy(self):
        return EconomyState(
            tick=10,
            running=True,
            tax_rate=0.10,
            items={
                "Health Potion": ItemState(name="Health Potion", price=1.0, supply=0),  # At floor, 0 supply
                "Iron Sword": ItemState(name="Iron Sword", price=50.0, supply=100),
                "Raw Gem": ItemState(name="Raw Gem", price=25.0, supply=50),
            },
            agents={
                "Insolvent": AgentState(name="Insolvent", persona="Broke", gold=0.0, inventory={}),
                "Middle": AgentState(name="Middle", persona="Worker", gold=50.0, inventory={}),
            },
            recent_transactions=[],
        )

    def test_dragon_attack_when_supply_is_zero_and_price_is_floor(self, extreme_economy):
        """Dragon Attack on 0-supply floor-price commodity resets supply=2 and price=35.0."""
        apply_dragon_attack(extreme_economy)

        potion = extreme_economy.items["Health Potion"]
        assert potion.supply == 2
        assert potion.price == 35.0

        # Invariants: other commodities and agents untouched
        assert extreme_economy.items["Iron Sword"].supply == 100
        assert extreme_economy.items["Iron Sword"].price == 50.0
        assert extreme_economy.agents["Insolvent"].gold == 0.0
        assert_state_invariants(extreme_economy)

    def test_dragon_attack_when_supply_is_massive(self, extreme_economy):
        """Dragon Attack on massive supply (10,000) crushes supply strictly down to 2."""
        extreme_economy.items["Health Potion"].supply = 10_000
        extreme_economy.items["Health Potion"].price = 250.0
        apply_dragon_attack(extreme_economy)

        potion = extreme_economy.items["Health Potion"]
        assert potion.supply == 2
        assert potion.price == 35.0

    def test_dragon_attack_when_potion_missing_from_catalog(self, extreme_economy):
        """Dragon Attack safely handles corrupted or missing catalog entry by inserting it."""
        del extreme_economy.items["Health Potion"]
        apply_dragon_attack(extreme_economy)

        assert "Health Potion" in extreme_economy.items
        assert extreme_economy.items["Health Potion"].supply == 2
        assert extreme_economy.items["Health Potion"].price == 35.0

    def test_dragon_attack_repeated_idempotence(self, extreme_economy):
        """Multiple consecutive Dragon Attack triggers maintain exactly supply=2 and price=35.0."""
        for _ in range(5):
            apply_dragon_attack(extreme_economy)
            assert extreme_economy.items["Health Potion"].supply == 2
            assert extreme_economy.items["Health Potion"].price == 35.0

    def test_gold_rush_with_zero_gold_agent(self, extreme_economy):
        """Gold Rush credits full +100.0 Gold to completely broke agents."""
        apply_gold_rush(extreme_economy, gold_amount=100.0)

        assert extreme_economy.agents["Insolvent"].gold == 100.0
        assert extreme_economy.agents["Middle"].gold == 150.0
        # Invariants: item catalog untouched
        assert extreme_economy.items["Health Potion"].price == 1.0
        assert extreme_economy.items["Health Potion"].supply == 0
        assert_state_invariants(extreme_economy)

    def test_gold_rush_fractional_credit(self, extreme_economy):
        """Gold Rush with fractional float credit rounds cleanly without precision loss."""
        apply_gold_rush(extreme_economy, gold_amount=0.33333)

        assert extreme_economy.agents["Insolvent"].gold == 0.33
        assert extreme_economy.agents["Middle"].gold == 50.33
        assert_state_invariants(extreme_economy)

    def test_gold_rush_zero_amount_invariance(self, extreme_economy):
        """Gold Rush with 0.0 amount is a clean no-op."""
        apply_gold_rush(extreme_economy, gold_amount=0.0)

        assert extreme_economy.agents["Insolvent"].gold == 0.0
        assert extreme_economy.agents["Middle"].gold == 50.0

    def test_gold_rush_additive_across_sequential_rounds(self, extreme_economy):
        """Consecutive Gold Rush events additively accumulate funds across ticks."""
        apply_gold_rush(extreme_economy, 100.0)  # 0 -> 100
        apply_gold_rush(extreme_economy, 100.0)  # 100 -> 200
        apply_gold_rush(extreme_economy, 100.0)  # 200 -> 300

        assert extreme_economy.agents["Insolvent"].gold == 300.0
        assert extreme_economy.agents["Middle"].gold == 350.0
        assert_state_invariants(extreme_economy)

    def test_combined_shock_dragon_attack_and_gold_rush_order_invariance(self, extreme_economy):
        """Applying Dragon Attack followed by Gold Rush leaves both effects intact."""
        apply_dragon_attack(extreme_economy)
        apply_gold_rush(extreme_economy, 100.0)

        assert extreme_economy.items["Health Potion"].supply == 2
        assert extreme_economy.items["Health Potion"].price == 35.0
        assert extreme_economy.agents["Insolvent"].gold == 100.0
        assert extreme_economy.agents["Middle"].gold == 150.0
        assert_state_invariants(extreme_economy)
