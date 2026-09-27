"""
Milestone 1 Iteration 2 Challenger Stress Verification Harness.
Author: teamwork_preview_challenger (m1_i2_challenger_1)

Empirical stress verification harness:
1. Rapid alternating BUY and SELL orders across variable tax rates (0.0, 0.10, 0.50, 0.80).
2. Symmetric tax withholding verification between buyer and seller.
3. Strict mathematical wealth and stock conservation invariants.
4. Arbitrage, rounding drift, and state leakage audits.
"""

import random
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


class TestChallengerAlternatingTaxStress:
    """Stress tests rapid alternating BUY and SELL orders under variable tax rates."""

    @pytest.mark.parametrize("tax_rate", [0.0, 0.10, 0.50, 0.80])
    def test_rapid_alternating_buy_sell_wealth_conservation(self, tax_rate: float):
        """
        Executes 100 rapid alternating BUY and SELL cycles on Health Potion.
        Verifies:
        - Symmetric tax withholding on BUY (added to cost) and SELL (withheld from proceeds).
        - Exact wealth conservation: Agent Gold + Total Taxes Collected = Initial Gold.
        - Exact commodity conservation: Market Supply + Agent Inventory = Initial Total Stock.
        """
        initial_price = 20.0
        initial_supply = 100
        initial_gold = 5000.0
        cycles = 100

        item = ItemState(name="Health Potion", price=initial_price, supply=initial_supply)
        agent = AgentState(
            name="TraderAgent",
            persona="StressTester",
            gold=initial_gold,
            inventory={"Health Potion": 0, "Iron Sword": 0, "Raw Gem": 0},
        )
        state = EconomyState(
            tick=1,
            running=True,
            tax_rate=tax_rate,
            items={"Health Potion": item},
            agents={"TraderAgent": agent},
            recent_transactions=[],
        )

        total_taxes_collected = 0.0

        for cycle in range(1, cycles + 1):
            state.tick = cycle
            # 1. BUY 1 unit
            buy_decision = AgentDecision(
                action=ActionType.BUY,
                item="Health Potion",
                quantity=1,
                reasoning=f"Cycle {cycle} BUY",
            )
            rec_buy = execute_transaction(state, "TraderAgent", buy_decision)
            assert rec_buy.status == "EXECUTED"

            # Verify symmetric tax calculation
            expected_tax = calculate_tax(initial_price, 1, tax_rate)
            assert rec_buy.tax_paid == expected_tax
            assert rec_buy.total_cost == round(initial_price + expected_tax, 2)
            total_taxes_collected = round(total_taxes_collected + rec_buy.tax_paid, 2)

            # Invariant check post-BUY: 1 unit in inventory, 1 less in market supply
            assert state.agents["TraderAgent"].inventory["Health Potion"] == 1
            assert state.items["Health Potion"].supply == initial_supply - 1

            # 2. SELL 1 unit
            sell_decision = AgentDecision(
                action=ActionType.SELL,
                item="Health Potion",
                quantity=1,
                reasoning=f"Cycle {cycle} SELL",
            )
            rec_sell = execute_transaction(state, "TraderAgent", sell_decision)
            assert rec_sell.status == "EXECUTED"

            # Verify symmetric tax withholding on SELL
            assert rec_sell.tax_paid == expected_tax
            assert rec_sell.total_cost == round(initial_price * 1.0, 2)
            total_taxes_collected = round(total_taxes_collected + rec_sell.tax_paid, 2)

            # Invariant check post-SELL: 0 units in inventory, supply restored to initial_supply
            assert state.agents["TraderAgent"].inventory["Health Potion"] == 0
            assert state.items["Health Potion"].supply == initial_supply

            # Mathematical Wealth Conservation Law:
            # Current Agent Gold + Total Cumulative Taxes Paid MUST strictly equal Initial Gold
            current_gold = state.agents["TraderAgent"].gold
            accounted_wealth = round(current_gold + total_taxes_collected, 2)
            assert accounted_wealth == initial_gold, (
                f"Tax rate {tax_rate}, Cycle {cycle}: Wealth leak detected! "
                f"Initial: {initial_gold}, Accounted: {accounted_wealth}, Diff: {accounted_wealth - initial_gold}"
            )

        # Terminal assertions
        assert_state_invariants(state)
        # At 0.0 tax, agent gold must be exactly equal to initial_gold (0 friction)
        if tax_rate == 0.0:
            assert state.agents["TraderAgent"].gold == initial_gold
            assert total_taxes_collected == 0.0
        else:
            # Each round trip incurs exactly 2 * expected_tax in friction
            expected_total_friction = round(2 * expected_tax * cycles, 2)
            assert total_taxes_collected == expected_total_friction
            assert state.agents["TraderAgent"].gold == round(initial_gold - expected_total_friction, 2)

    def test_multi_agent_concurrent_trading_wealth_conservation(self):
        """
        Tests multi-agent simultaneous BUY/SELL trading within the same tick.
        Agent A buys from market, Agent B sells to market.
        Verifies global conservation of gold, goods, and tax treasury across tax rate changes.
        """
        tax_rates = [0.0, 0.10, 0.50, 0.80]

        for tax_rate in tax_rates:
            state = EconomyState(
                tick=1,
                tax_rate=tax_rate,
                items={
                    "Health Potion": ItemState(name="Health Potion", price=20.0, supply=50),
                    "Iron Sword": ItemState(name="Iron Sword", price=30.0, supply=50),
                    "Raw Gem": ItemState(name="Raw Gem", price=15.0, supply=50),
                },
                agents={
                    "Buyer": AgentState(name="Buyer", persona="Buyer", gold=1000.0, inventory={"Health Potion": 0}),
                    "Seller": AgentState(name="Seller", persona="Seller", gold=1000.0, inventory={"Health Potion": 10}),
                },
                recent_transactions=[],
            )

            initial_agent_gold = sum(a.gold for a in state.agents.values())
            initial_potion_stock = state.items["Health Potion"].supply + sum(
                a.inventory.get("Health Potion", 0) for a in state.agents.values()
            )

            # Buyer buys 2 Health Potions
            dec_buy = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=2, reasoning="Buy")
            rec_buy = execute_transaction(state, "Buyer", dec_buy)
            assert rec_buy.status == "EXECUTED"

            # Seller sells 2 Health Potions
            dec_sell = AgentDecision(action=ActionType.SELL, item="Health Potion", quantity=2, reasoning="Sell")
            rec_sell = execute_transaction(state, "Seller", dec_sell)
            assert rec_sell.status == "EXECUTED"

            # Taxes paid
            tax_buy = rec_buy.tax_paid
            tax_sell = rec_sell.tax_paid
            assert tax_buy == tax_sell  # Symmetric tax withholding check

            # Global gold and commodity conservation
            total_tax_collected = tax_buy + tax_sell
            current_agent_gold = sum(a.gold for a in state.agents.values())
            assert round(current_agent_gold + total_tax_collected, 2) == initial_agent_gold

            current_potion_stock = state.items["Health Potion"].supply + sum(
                a.inventory.get("Health Potion", 0) for a in state.agents.values()
            )
            assert current_potion_stock == initial_potion_stock

            # Update market prices with tick transactions
            net_demand = calculate_net_demand([rec_buy, rec_sell], "Health Potion")
            assert net_demand == 0  # 2 bought - 2 sold = 0
            new_prices = update_market_prices(state, [rec_buy, rec_sell], k=0.05)
            assert new_prices["Health Potion"] == 20.0  # Zero drift under balanced demand
