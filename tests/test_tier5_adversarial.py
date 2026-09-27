"""
Tier 5 Adversarial Stress Testing Suite for Milestone 1.

Comprehensive adversarial test suite covering:
1. Market Supply Exhaustion (consecutive BUYs draining supply to exactly 0, and clean rejections).
2. Solvency Boundary Conditions (exact gold, 0.01 deficit, 1e-7 sub-cent boundary, zero gold).
3. Precision Rounding Drift Harness (500 randomized transactions, conservation laws, float stability).
4. Draft-07 JSON Schema Boundaries (AgentDecision, ItemState, AgentState, EconomyState).
5. Audit Log Idempotency & Deduplication (state.recent_transactions duplicate rejection, loop iterations, cross-tick time-series).
"""

import random
import pytest
from pydantic import ValidationError

from src.models import (
    ActionType,
    AgentDecision,
    ItemState,
    AgentState,
    EconomyState,
    TransactionRecord,
    AGENT_DECISION_DRAFT07_SCHEMA,
    VALID_ITEMS,
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
# 1. MARKET SUPPLY EXHAUSTION ADVERSARIAL TESTS
# ============================================================================

class TestMarketSupplyExhaustionAdversarial:
    """
    Adversarial challenge: draining market commodity supply to exactly 0 units
    across multiple consecutive BUY orders, verifying subsequent orders fail cleanly
    without state corruption, and verifying supply replenishment via SELL.
    """

    @pytest.fixture
    def scarce_market_state(self):
        """Creates an economy with strictly finite, scarce commodity supply."""
        return EconomyState(
            tick=1,
            running=True,
            tax_rate=0.10,
            items={
                "Health Potion": ItemState(name="Health Potion", price=20.0, supply=5),
                "Iron Sword": ItemState(name="Iron Sword", price=30.0, supply=1),
                "Raw Gem": ItemState(name="Raw Gem", price=15.0, supply=0),
            },
            agents={
                "Garrick": AgentState(
                    name="Garrick",
                    persona="Garrick the Greedy",
                    gold=1000.0,
                    inventory={"Health Potion": 0, "Iron Sword": 0, "Raw Gem": 5},
                ),
                "Cora": AgentState(
                    name="Cora",
                    persona="Cora the Farmer",
                    gold=500.0,
                    inventory={"Health Potion": 0, "Iron Sword": 0, "Raw Gem": 0},
                ),
            },
            recent_transactions=[],
        )

    def test_drain_supply_to_exact_zero_and_reject_subsequent(self, scarce_market_state):
        """
        Consecutive BUY orders drain Health Potion supply: 5 -> 3 -> 1 -> 0.
        All subsequent BUY orders MUST be cleanly rejected, supply MUST stay 0,
        and agent funds MUST NOT be debited.
        """
        state = scarce_market_state
        initial_gold = state.agents["Garrick"].gold

        # Order 1: Buy 2 units (5 -> 3)
        dec1 = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=2, reasoning="Drain 1")
        rec1 = execute_transaction(state, "Garrick", dec1)
        assert rec1.status == "EXECUTED"
        assert state.items["Health Potion"].supply == 3
        assert state.agents["Garrick"].inventory["Health Potion"] == 2

        # Order 2: Buy 2 units (3 -> 1)
        dec2 = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=2, reasoning="Drain 2")
        rec2 = execute_transaction(state, "Garrick", dec2)
        assert rec2.status == "EXECUTED"
        assert state.items["Health Potion"].supply == 1
        assert state.agents["Garrick"].inventory["Health Potion"] == 4

        # Order 3: Buy 1 unit (1 -> 0, exactly exhausted)
        dec3 = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Drain 3 to zero")
        rec3 = execute_transaction(state, "Garrick", dec3)
        assert rec3.status == "EXECUTED"
        assert state.items["Health Potion"].supply == 0
        assert state.agents["Garrick"].inventory["Health Potion"] == 5

        # Record gold balance after all 5 units purchased: 5 * 20.0 * 1.10 = 110.0 total cost
        gold_at_zero_supply = state.agents["Garrick"].gold
        assert gold_at_zero_supply == initial_gold - 110.0

        # Order 4: BUY 1 unit when supply is 0 -> MUST REJECT
        dec4 = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Attempt buy at zero")
        rec4 = execute_transaction(state, "Garrick", dec4)
        assert rec4.status == "REJECTED"
        assert "insufficient market supply" in rec4.reason.lower()
        assert state.items["Health Potion"].supply == 0
        assert state.agents["Garrick"].gold == gold_at_zero_supply
        assert state.agents["Garrick"].inventory["Health Potion"] == 5

        # Order 5: BUY 10 units when supply is 0 -> MUST REJECT
        dec5 = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=10, reasoning="Bulk attempt at zero")
        rec5 = execute_transaction(state, "Garrick", dec5)
        assert rec5.status == "REJECTED"
        assert state.items["Health Potion"].supply == 0
        assert state.agents["Garrick"].gold == gold_at_zero_supply

        # Order 6: Another agent (Cora) attempts to buy -> MUST ALSO REJECT
        dec6 = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Cora attempt")
        rec6 = execute_transaction(state, "Cora", dec6)
        assert rec6.status == "REJECTED"
        assert state.items["Health Potion"].supply == 0
        assert state.agents["Cora"].gold == 500.0

    def test_supply_replenishment_via_sell_after_exhaustion(self, scarce_market_state):
        """After supply is 0, a SELL order restores available stock and permits subsequent BUY."""
        state = scarce_market_state
        assert state.items["Raw Gem"].supply == 0  # Starts at 0

        # Attempt to buy Raw Gem at 0 supply -> REJECTED
        dec_buy_fail = AgentDecision(action=ActionType.BUY, item="Raw Gem", quantity=1, reasoning="Buy gem at 0")
        rec_fail = execute_transaction(state, "Cora", dec_buy_fail)
        assert rec_fail.status == "REJECTED"

        # Garrick SELLS 3 Raw Gems into the market
        dec_sell = AgentDecision(action=ActionType.SELL, item="Raw Gem", quantity=3, reasoning="Sell 3 gems")
        rec_sell = execute_transaction(state, "Garrick", dec_sell)
        assert rec_sell.status == "EXECUTED"
        assert state.items["Raw Gem"].supply == 3
        assert state.agents["Garrick"].inventory["Raw Gem"] == 2

        # Cora now buys 2 Raw Gems -> EXECUTED (supply drops from 3 to 1)
        dec_buy_ok = AgentDecision(action=ActionType.BUY, item="Raw Gem", quantity=2, reasoning="Buy replenished gems")
        rec_ok = execute_transaction(state, "Cora", dec_buy_ok)
        assert rec_ok.status == "EXECUTED"
        assert state.items["Raw Gem"].supply == 1
        assert state.agents["Cora"].inventory["Raw Gem"] == 2

    def test_net_demand_ignores_exhausted_rejected_orders(self, scarce_market_state):
        """Net demand calculation strictly counts EXECUTED orders, ignoring exhausted rejections."""
        state = scarce_market_state
        # Single unit available
        dec1 = AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=1, reasoning="Buy only sword")
        execute_transaction(state, "Garrick", dec1)

        # 3 rejected buy attempts for 2, 5, 10 swords
        for q in [2, 5, 10]:
            dec_rej = AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=q, reasoning="Over-demand")
            execute_transaction(state, "Garrick", dec_rej)

        delta_d = calculate_net_demand(state.recent_transactions, "Iron Sword")
        assert delta_d == 1  # Only the single executed buy counts; phantom demand is excluded


# ============================================================================
# 2. SOLVENCY BOUNDARY ADVERSARIAL TESTS
# ============================================================================

class TestSolvencyBoundaryAdversarial:
    """
    Adversarial challenge: stress-testing solvency boundaries when agent funds
    are exact, deficient by 1 cent ($0.01), deficient by sub-cent epsilon ($10^-7),
    or zero.
    """

    @pytest.fixture
    def standard_item(self):
        return ItemState(name="Health Potion", price=20.0, supply=10)

    def test_solvency_exact_gold_clean_execution(self, standard_item):
        """Agent gold exactly equals total_cost (unit_price * quantity + tax)."""
        tax = calculate_tax(standard_item.price, 1, 0.10)  # 2.00
        cost = round(standard_item.price + tax, 2)  # 22.00

        agent = AgentState(name="ExactAgent", persona="Tester", gold=cost, inventory={})
        valid, msg = validate_transaction(agent, standard_item, ActionType.BUY, 1, 0.10)
        assert valid is True

        state = EconomyState(
            tick=1, tax_rate=0.10,
            items={"Health Potion": standard_item},
            agents={"ExactAgent": agent},
        )
        dec = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Exact buy")
        rec = execute_transaction(state, "ExactAgent", dec)

        assert rec.status == "EXECUTED"
        assert state.agents["ExactAgent"].gold == 0.00
        assert_state_invariants(state)

    def test_solvency_cent_deficit_strictly_rejected(self, standard_item):
        """Agent gold is deficient by exactly 1 cent (21.99 vs 22.00). Must be rejected."""
        agent = AgentState(name="PoorAgent", persona="Tester", gold=21.99, inventory={})
        valid, msg = validate_transaction(agent, standard_item, ActionType.BUY, 1, 0.10)
        assert valid is False
        assert "insufficient gold" in msg.lower()

        state = EconomyState(
            tick=1, tax_rate=0.10,
            items={"Health Potion": standard_item},
            agents={"PoorAgent": agent},
        )
        dec = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Deficit buy")
        rec = execute_transaction(state, "PoorAgent", dec)
        assert rec.status == "REJECTED"
        assert state.agents["PoorAgent"].gold == 21.99  # Untouched

    def test_solvency_subcent_epsilon_boundary(self, standard_item):
        """
        Adversarial evaluation of sub-cent epsilon 0.0000001 (1e-7).
        In the financial model with 2-decimal rounding:
        - When instantiated via Pydantic AgentState, gold=21.9999999 rounds to 22.00.
        - If mutated via attribute agent.gold = 21.9999999, round(agent.gold, 2) rounds to 22.00.
        - Execution round(agent.gold - total_cost, 2) yields 0.00 without negative balance.
        """
        # Case A: Instantiated via model
        agent_pydantic = AgentState(name="SubcentA", persona="Tester", gold=21.9999999, inventory={})
        assert agent_pydantic.gold == 22.00  # Pydantic validator rounds to 2 decimal places

        # Case B: Mutated directly on attribute
        agent_mutated = AgentState(name="SubcentB", persona="Tester", gold=22.00, inventory={})
        agent_mutated.gold = 22.00 - 1e-7  # 21.9999999

        valid, msg = validate_transaction(agent_mutated, standard_item, ActionType.BUY, 1, 0.10)
        assert valid is True

        state = EconomyState(
            tick=1, tax_rate=0.10,
            items={"Health Potion": standard_item},
            agents={"SubcentB": agent_mutated},
        )
        dec = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Subcent buy")
        rec = execute_transaction(state, "SubcentB", dec)
        assert rec.status == "EXECUTED"
        assert state.agents["SubcentB"].gold == 0.00  # Does NOT go negative
        assert_state_invariants(state)

    def test_solvency_half_cent_deficit_boundary(self, standard_item):
        """
        Deficit below half a cent (e.g. 21.994 vs 22.00) rounds down to 21.99
        and MUST be rejected.
        """
        agent = AgentState(name="HalfCent", persona="Tester", gold=21.994, inventory={})
        # Pydantic rounds 21.994 to 21.99
        assert agent.gold == 21.99
        valid, msg = validate_transaction(agent, standard_item, ActionType.BUY, 1, 0.10)
        assert valid is False

    def test_solvency_zero_gold_agent_behavior(self, standard_item):
        """Agent with 0.00 Gold can SELL and HOLD, but cannot BUY."""
        agent = AgentState(name="BrokeAgent", persona="Tester", gold=0.00, inventory={"Health Potion": 2})
        state = EconomyState(
            tick=1, tax_rate=0.10,
            items={"Health Potion": standard_item},
            agents={"BrokeAgent": agent},
        )

        # BUY rejected
        dec_buy = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Broke buy")
        rec_buy = execute_transaction(state, "BrokeAgent", dec_buy)
        assert rec_buy.status == "REJECTED"
        assert state.agents["BrokeAgent"].gold == 0.00

        # HOLD executed
        dec_hold = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Broke hold")
        rec_hold = execute_transaction(state, "BrokeAgent", dec_hold)
        assert rec_hold.status == "EXECUTED"
        assert state.agents["BrokeAgent"].gold == 0.00

        # SELL executed, earning revenue
        dec_sell = AgentDecision(action=ActionType.SELL, item="Health Potion", quantity=1, reasoning="Broke sell")
        rec_sell = execute_transaction(state, "BrokeAgent", dec_sell)
        assert rec_sell.status == "EXECUTED"
        assert state.agents["BrokeAgent"].gold == 18.00  # Net revenue credited after 10% tax (20.0 - 2.0)
        assert state.agents["BrokeAgent"].inventory["Health Potion"] == 1


# ============================================================================
# 3. PRECISION ROUNDING DRIFT HARNESS (500 RANDOMIZED TRANSACTIONS)
# ============================================================================

class TestPrecisionRoundingDriftAdversarial:
    """
    Stress harness executing 500 randomized transactions across 3 agents and 3 items.
    Verifies:
    1. Zero floating-point representation drift (all gold and prices round to 2 decimals).
    2. Conservation of total physical commodity inventory across the simulation.
    3. Global state invariants after every transaction and at terminal state.
    """

    def test_randomized_500_transactions_precision_and_conservation(self):
        """
        Executes 500 pseudo-random transactions (seeded for deterministic reproducibility).
        Audits balance precision, price discovery floor, tax calculation, and commodity stock conservation.
        """
        rng = random.Random(42)

        # Baseline items with ample initial supply
        items = {
            "Health Potion": ItemState(name="Health Potion", price=20.0, supply=300),
            "Iron Sword": ItemState(name="Iron Sword", price=30.0, supply=300),
            "Raw Gem": ItemState(name="Raw Gem", price=15.0, supply=300),
        }
        # Baseline agents with balanced starting wealth and goods
        agents = {
            "Garrick": AgentState(
                name="Garrick", persona="Greedy", gold=1500.0,
                inventory={"Health Potion": 50, "Iron Sword": 50, "Raw Gem": 50},
            ),
            "Cora": AgentState(
                name="Cora", persona="Farmer", gold=1500.0,
                inventory={"Health Potion": 50, "Iron Sword": 50, "Raw Gem": 50},
            ),
            "Boran": AgentState(
                name="Boran", persona="Adventurer", gold=1500.0,
                inventory={"Health Potion": 50, "Iron Sword": 50, "Raw Gem": 50},
            ),
        }

        # Calculate initial total stock in universe for each commodity
        initial_total_stock = {
            item_name: items[item_name].supply + sum(ag.inventory[item_name] for ag in agents.values())
            for item_name in items
        }

        state = EconomyState(
            tick=0,
            running=True,
            tax_rate=0.10,
            items=items,
            agents=agents,
            recent_transactions=[],
        )

        item_names = list(items.keys())
        agent_names = list(agents.keys())
        actions = [ActionType.BUY, ActionType.SELL, ActionType.HOLD]
        tax_rates = [0.0, 0.05, 0.10, 0.20, 0.50, 0.80]

        executed_count = 0
        rejected_count = 0

        # Execute 500 continuous transactions
        for tx_idx in range(1, 501):
            agent_name = rng.choice(agent_names)
            action = rng.choice(actions)
            item_name = rng.choice(item_names) if action != ActionType.HOLD else None
            quantity = rng.randint(1, 10)

            # Periodically shift macroeconomic tax rate
            if tx_idx % 50 == 0:
                state.tax_rate = rng.choice(tax_rates)

            decision = AgentDecision(
                action=action,
                item=item_name,
                quantity=quantity,
                reasoning=f"Adversarial tx {tx_idx}",
            )

            record = execute_transaction(state, agent_name, decision)

            if record.status == "EXECUTED":
                executed_count += 1
            else:
                rejected_count += 1

            # Periodically trigger market price updates (every 25 transactions)
            if tx_idx % 25 == 0:
                state.tick += 1
                recent_window = state.recent_transactions[-25:]
                update_market_prices(state, recent_window, k=0.05, min_price=1.0)

            # --- Intermediate Precision Audit ---
            # 1. Price precision (must strictly have at most 2 decimal digits)
            for it_name, it_state in state.items.items():
                assert round(it_state.price, 2) == it_state.price, (
                    f"Tx {tx_idx}: Price precision drift on {it_name}: {it_state.price}"
                )
                assert it_state.price >= 1.0, f"Tx {tx_idx}: Price floor violated on {it_name}: {it_state.price}"
                assert it_state.supply >= 0, f"Tx {tx_idx}: Negative supply on {it_name}: {it_state.supply}"

            # 2. Agent gold precision
            for ag_name, ag_state in state.agents.items():
                assert round(ag_state.gold, 2) == round(ag_state.gold, 4), (
                    f"Tx {tx_idx}: Gold precision drift on {ag_name}: {ag_state.gold}"
                )
                assert ag_state.gold >= 0.0, f"Tx {tx_idx}: Negative gold on {ag_name}: {ag_state.gold}"

            # 3. Commodity Stock Conservation
            for it_name in item_names:
                current_stock = state.items[it_name].supply + sum(
                    ag.inventory.get(it_name, 0) for ag in state.agents.values()
                )
                assert current_stock == initial_total_stock[it_name], (
                    f"Tx {tx_idx}: Conservation violated for {it_name}: "
                    f"expected {initial_total_stock[it_name]}, got {current_stock}"
                )

        # Terminal state audits
        assert executed_count + rejected_count == 500
        assert executed_count > 0, "No transactions were executed"
        assert_state_invariants(state)


# ============================================================================
# 4. MODEL SCHEMA BOUNDARIES & DRAFT-07 COMPLIANCE
# ============================================================================

class TestModelSchemaBoundariesAdversarial:
    """
    Adversarial challenge: schema boundary probing on AgentDecision, ItemState,
    AgentState, and EconomyState against Draft-07 JSON Schema specifications.
    """

    def test_agent_decision_draft07_schema_metadata(self):
        """Verifies Draft-07 schema specifications attached to AgentDecision."""
        schema = AGENT_DECISION_DRAFT07_SCHEMA
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema["type"] == "object"
        assert set(schema["required"]) == {"action", "item", "quantity", "reasoning"}
        assert schema["properties"]["quantity"]["minimum"] == 1
        assert schema["properties"]["quantity"]["maximum"] == 10
        assert schema["properties"]["reasoning"]["maxLength"] == 120
        assert set(schema["properties"]["action"]["enum"]) == {"BUY", "SELL", "HOLD", "CRAFT"}

    def test_agent_decision_quantity_boundary_extremes(self):
        """Tests quantity boundaries: 1 (min valid), 10 (max valid), 0, -1, 11 (invalid)."""
        # Valid boundaries
        d_min = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=1, reasoning="Min")
        assert d_min.quantity == 1
        d_max = AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=10, reasoning="Max")
        assert d_max.quantity == 10

        # Invalid boundaries
        with pytest.raises(ValidationError):
            AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=0, reasoning="Underflow")
        with pytest.raises(ValidationError):
            AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=-1, reasoning="Negative")
        with pytest.raises(ValidationError):
            AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=11, reasoning="Overflow")
        with pytest.raises(ValidationError):
            AgentDecision(action=ActionType.BUY, item="Health Potion", quantity=100, reasoning="Large overflow")

    def test_agent_decision_reasoning_length_boundaries(self):
        """Tests reasoning length boundaries: 0, 1, 120 (valid), 121 (invalid)."""
        d_empty = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="")
        assert d_empty.reasoning == ""

        d_1 = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="X")
        assert len(d_1.reasoning) == 1

        d_120 = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Z" * 120)
        assert len(d_120.reasoning) == 120

        with pytest.raises(ValidationError):
            AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Z" * 121)

    def test_agent_decision_item_validation(self):
        """Tests item literal boundaries: valid catalog items vs invalid strings."""
        for item in VALID_ITEMS:
            d = AgentDecision(action=ActionType.BUY, item=item, quantity=1, reasoning="Valid item")
            assert d.item == item

        # None is valid for HOLD
        d_none = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Hold None")
        assert d_none.item is None

        # Invalid item name raises ValidationError
        with pytest.raises(ValidationError):
            AgentDecision(action=ActionType.BUY, item="Excalibur", quantity=1, reasoning="Invalid item")

    def test_item_state_price_floor_boundary(self):
        """Tests ItemState price boundary: 1.0 (valid), 0.999 (invalid)."""
        item_floor = ItemState(name="Health Potion", price=1.0, supply=10)
        assert item_floor.price == 1.0

        with pytest.raises(ValidationError):
            ItemState(name="Health Potion", price=0.99, supply=10)

        with pytest.raises(ValidationError):
            ItemState(name="Health Potion", price=-1.0, supply=10)

    def test_item_state_supply_non_negative_boundary(self):
        """Tests ItemState supply boundary: 0 (valid), -1 (invalid)."""
        item_zero = ItemState(name="Health Potion", price=20.0, supply=0)
        assert item_zero.supply == 0

        with pytest.raises(ValidationError):
            ItemState(name="Health Potion", price=20.0, supply=-1)

    def test_agent_state_gold_non_negative_boundary(self):
        """Tests AgentState gold boundary: 0.0 (valid), -0.01 (invalid)."""
        agent_zero = AgentState(name="Broke", persona="Tester", gold=0.0, inventory={})
        assert agent_zero.gold == 0.0

        with pytest.raises(ValidationError):
            AgentState(name="Negative", persona="Tester", gold=-0.01, inventory={})

    def test_agent_state_negative_inventory_rejected(self):
        """Tests AgentState inventory validator rejects negative counts."""
        with pytest.raises(ValidationError) as exc_info:
            AgentState(name="Cheater", persona="Tester", gold=100.0, inventory={"Health Potion": -1})
        assert "cannot be negative" in str(exc_info.value)

    def test_economy_state_tax_rate_boundaries(self):
        """Tests EconomyState tax rate boundaries [0.0, 0.80]."""
        state_0 = EconomyState(tax_rate=0.0, items={}, agents={})
        assert state_0.tax_rate == 0.0

        state_80 = EconomyState(tax_rate=0.80, items={}, agents={})
        assert state_80.tax_rate == 0.80

        with pytest.raises(ValidationError):
            EconomyState(tax_rate=-0.01, items={}, agents={})

        with pytest.raises(ValidationError):
            EconomyState(tax_rate=0.81, items={}, agents={})


# ============================================================================
# 5. AUDIT LOG IDEMPOTENCY & TRANSACTION DEDUPLICATION ADVERSARIAL TESTS
# ============================================================================

class TestAuditLogDeduplicationAdversarial:
    """
    Adversarial challenge: verify deduplication in state.recent_transactions
    under repeat execution, replay attacks, and loop iterations.
    """

    @pytest.fixture
    def deduplication_state(self):
        return EconomyState(
            tick=1,
            running=True,
            tax_rate=0.10,
            items={
                "Health Potion": ItemState(name="Health Potion", price=20.0, supply=10),
                "Iron Sword": ItemState(name="Iron Sword", price=30.0, supply=0),  # 0 supply
            },
            agents={
                "Garrick": AgentState(
                    name="Garrick",
                    persona="Garrick the Greedy",
                    gold=100.0,
                    inventory={"Health Potion": 2, "Iron Sword": 0},
                ),
                "Cora": AgentState(
                    name="Cora",
                    persona="Cora the Farmer",
                    gold=50.0,
                    inventory={"Health Potion": 0, "Iron Sword": 0},
                ),
            },
            recent_transactions=[],
        )

    def test_repeat_execution_deduplication_same_tick(self, deduplication_state):
        """Repeated execution of identical HOLD action at same tick does not duplicate audit record."""
        state = deduplication_state
        dec = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Holding")

        rec1 = execute_transaction(state, "Garrick", dec)
        assert len(state.recent_transactions) == 1
        assert rec1.status == "EXECUTED"

        # Re-execute exact same action within same tick
        rec2 = execute_transaction(state, "Garrick", dec)
        assert len(state.recent_transactions) == 1
        assert rec1 == rec2

    def test_repeat_execution_loop_ten_iterations(self, deduplication_state):
        """Executing 10 identical transactions in a tight loop maintains strictly 1 audit record."""
        state = deduplication_state
        dec = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Loop hold")

        for _ in range(10):
            execute_transaction(state, "Garrick", dec)

        assert len(state.recent_transactions) == 1
        assert state.recent_transactions[0].agent_name == "Garrick"
        assert state.recent_transactions[0].action == ActionType.HOLD

    def test_rejected_order_deduplication_under_repeat_calls(self, deduplication_state):
        """Identical rejected BUY attempts (e.g. at 0 market supply) are deduplicated in audit log."""
        state = deduplication_state
        # Iron Sword has supply = 0
        dec_rejected = AgentDecision(action=ActionType.BUY, item="Iron Sword", quantity=1, reasoning="Buy at 0")

        rec1 = execute_transaction(state, "Garrick", dec_rejected)
        assert rec1.status == "REJECTED"
        assert len(state.recent_transactions) == 1

        # Second identical rejected call
        rec2 = execute_transaction(state, "Garrick", dec_rejected)
        assert rec2.status == "REJECTED"
        assert len(state.recent_transactions) == 1
        assert rec1 == rec2

    def test_cross_tick_identical_actions_recorded_per_tick(self, deduplication_state):
        """Cross-tick identical actions have distinct tick indices and are NOT deduplicated."""
        state = deduplication_state
        dec = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Holding across ticks")

        # Tick 1 execution
        state.tick = 1
        execute_transaction(state, "Garrick", dec)
        assert len(state.recent_transactions) == 1
        assert state.recent_transactions[0].tick == 1

        # Tick 2 execution of identical action
        state.tick = 2
        execute_transaction(state, "Garrick", dec)
        assert len(state.recent_transactions) == 2
        assert state.recent_transactions[1].tick == 2

        # Tick 3 execution of identical action
        state.tick = 3
        execute_transaction(state, "Garrick", dec)
        assert len(state.recent_transactions) == 3
        assert state.recent_transactions[2].tick == 3

    def test_distinct_agents_same_tick_not_deduplicated(self, deduplication_state):
        """Different agents performing identical action types in the same tick are distinct."""
        state = deduplication_state
        dec_garrick = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Sync hold")
        dec_cora = AgentDecision(action=ActionType.HOLD, item=None, quantity=1, reasoning="Sync hold")

        execute_transaction(state, "Garrick", dec_garrick)
        assert len(state.recent_transactions) == 1

        execute_transaction(state, "Cora", dec_cora)
        assert len(state.recent_transactions) == 2
        assert state.recent_transactions[0].agent_name == "Garrick"
        assert state.recent_transactions[1].agent_name == "Cora"

    def test_transaction_record_equality_semantics(self):
        """Direct Pydantic equality semantics ensure duplicate detection operates correctly."""
        rec_a = TransactionRecord(
            tick=1, agent_name="Garrick", action=ActionType.BUY, item="Health Potion",
            quantity=2, unit_price=20.0, tax_paid=4.0, total_cost=44.0, status="EXECUTED",
            reason="Order OK"
        )
        rec_b = TransactionRecord(
            tick=1, agent_name="Garrick", action=ActionType.BUY, item="Health Potion",
            quantity=2, unit_price=20.0, tax_paid=4.0, total_cost=44.0, status="EXECUTED",
            reason="Order OK"
        )
        rec_c = TransactionRecord(
            tick=2, agent_name="Garrick", action=ActionType.BUY, item="Health Potion",
            quantity=2, unit_price=20.0, tax_paid=4.0, total_cost=44.0, status="EXECUTED",
            reason="Order OK"
        )

        assert rec_a == rec_b
        assert rec_a in [rec_b]
        assert rec_a != rec_c
        assert rec_c not in [rec_a, rec_b]

