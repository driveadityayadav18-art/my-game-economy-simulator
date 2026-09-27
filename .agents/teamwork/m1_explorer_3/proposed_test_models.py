"""
Unit Test Suite for src/models.py (Milestone 1).

Tests:
1. ActionType enum values (BUY, SELL, HOLD, CRAFT).
2. AgentDecision schema constraints (quantity bounds [1, 10], reasoning length <= 120, null item on HOLD).
3. ItemState validation (price >= 1.0, supply >= 0).
4. AgentState validation (gold >= 0.0, inventory mapping).
5. TransactionRecord fields and status enum.
6. EconomyState validation (tax_rate clamping [0.0, 0.80], items, agents).
7. Policy requests validation (PolicyTaxRequest, PolicyEventRequest).
"""

import pytest
from pydantic import ValidationError
from src.models import (
    ActionType,
    AgentDecision,
    AgentState,
    EconomyState,
    ItemState,
    TransactionRecord,
    PolicyTaxRequest,
    PolicyEventRequest,
)


class TestActionTypeEnum:
    """Tests ActionType enumeration members and string values."""

    def test_action_enum_values(self):
        assert ActionType.BUY == "BUY"
        assert ActionType.SELL == "SELL"
        assert ActionType.HOLD == "HOLD"
        assert ActionType.CRAFT == "CRAFT"

    def test_action_enum_string_serialization(self):
        assert ActionType.BUY.value == "BUY"
        assert ActionType.SELL.value == "SELL"


class TestAgentDecisionModel:
    """Tests AgentDecision schema validation, quantity limits, reasoning length."""

    def test_valid_decision_buy(self):
        decision = AgentDecision(
            action=ActionType.BUY,
            item="Health Potion",
            quantity=1,
            reasoning="Need health for quest",
        )
        assert decision.action == ActionType.BUY
        assert decision.item == "Health Potion"
        assert decision.quantity == 1
        assert decision.reasoning == "Need health for quest"

    def test_valid_decision_hold_with_none_item(self):
        decision = AgentDecision(
            action=ActionType.HOLD,
            item=None,
            quantity=1,
            reasoning="Holding steady",
        )
        assert decision.action == ActionType.HOLD
        assert decision.item is None

    def test_quantity_lower_boundary_one(self):
        decision = AgentDecision(
            action=ActionType.BUY,
            item="Iron Sword",
            quantity=1,
            reasoning="Minimum quantity",
        )
        assert decision.quantity == 1

    def test_quantity_upper_boundary_ten(self):
        decision = AgentDecision(
            action=ActionType.SELL,
            item="Raw Gem",
            quantity=10,
            reasoning="Maximum quantity",
        )
        assert decision.quantity == 10

    def test_quantity_zero_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AgentDecision(
                action=ActionType.BUY,
                item="Health Potion",
                quantity=0,
                reasoning="Zero quantity not allowed",
            )

    def test_quantity_negative_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AgentDecision(
                action=ActionType.BUY,
                item="Health Potion",
                quantity=-1,
                reasoning="Negative quantity",
            )

    def test_quantity_exceeding_ten_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AgentDecision(
                action=ActionType.BUY,
                item="Health Potion",
                quantity=11,
                reasoning="Too many items",
            )

    def test_reasoning_maximum_length_120(self):
        valid_reasoning = "A" * 120
        decision = AgentDecision(
            action=ActionType.HOLD,
            item=None,
            quantity=1,
            reasoning=valid_reasoning,
        )
        assert len(decision.reasoning) == 120

    def test_reasoning_exceeding_120_raises_validation_error(self):
        invalid_reasoning = "A" * 121
        with pytest.raises(ValidationError):
            AgentDecision(
                action=ActionType.HOLD,
                item=None,
                quantity=1,
                reasoning=invalid_reasoning,
            )

    def test_missing_reasoning_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AgentDecision(action=ActionType.HOLD, item=None, quantity=1)  # type: ignore


class TestItemStateModel:
    """Tests ItemState schema invariants."""

    def test_valid_item_state(self):
        item = ItemState(name="Health Potion", price=20.0, supply=100)
        assert item.price == 20.0
        assert item.supply == 100

    def test_item_price_at_floor(self):
        item = ItemState(name="Health Potion", price=1.0, supply=50)
        assert item.price == 1.0

    def test_item_price_below_floor_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ItemState(name="Health Potion", price=0.99, supply=50)

    def test_item_supply_zero_is_valid(self):
        item = ItemState(name="Health Potion", price=20.0, supply=0)
        assert item.supply == 0

    def test_item_negative_supply_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ItemState(name="Health Potion", price=20.0, supply=-1)


class TestAgentStateModel:
    """Tests AgentState schema invariants."""

    def test_valid_agent_state(self):
        agent = AgentState(
            name="Garrick",
            persona="Garrick the Greedy",
            gold=150.0,
            inventory={"Health Potion": 2, "Iron Sword": 1},
        )
        assert agent.gold == 150.0
        assert agent.inventory["Health Potion"] == 2

    def test_agent_gold_zero_is_valid(self):
        agent = AgentState(name="Boran", persona="Boran the Adventurer", gold=0.0, inventory={})
        assert agent.gold == 0.0

    def test_agent_negative_gold_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AgentState(name="Boran", persona="Boran the Adventurer", gold=-0.01, inventory={})


class TestTransactionRecordModel:
    """Tests TransactionRecord serialization and fields."""

    def test_valid_transaction_record(self):
        record = TransactionRecord(
            tick=1,
            agent_name="Garrick",
            action=ActionType.BUY,
            item="Health Potion",
            quantity=2,
            unit_price=20.0,
            tax_paid=4.0,
            total_cost=44.0,
            status="EXECUTED",
            reason="Order filled",
        )
        assert record.status == "EXECUTED"
        assert record.total_cost == 44.0

    def test_rejected_transaction_record(self):
        record = TransactionRecord(
            tick=1,
            agent_name="Boran",
            action=ActionType.BUY,
            item="Iron Sword",
            quantity=1,
            unit_price=30.0,
            tax_paid=0.0,
            total_cost=0.0,
            status="REJECTED",
            reason="Insufficient gold",
        )
        assert record.status == "REJECTED"


class TestEconomyStateModel:
    """Tests EconomyState macroeconomic tax bounds and nested collections."""

    def test_valid_economy_state(self):
        state = EconomyState(
            tick=0,
            running=False,
            tax_rate=0.10,
            items={"Health Potion": ItemState(name="Health Potion", price=20.0, supply=100)},
            agents={"Garrick": AgentState(name="Garrick", persona="Greedy", gold=150.0, inventory={})},
            recent_transactions=[],
        )
        assert state.tax_rate == 0.10
        assert state.tick == 0

    def test_tax_rate_minimum_bound(self):
        state = EconomyState(tick=0, tax_rate=0.0, items={}, agents={})
        assert state.tax_rate == 0.0

    def test_tax_rate_maximum_bound(self):
        state = EconomyState(tick=0, tax_rate=0.80, items={}, agents={})
        assert state.tax_rate == 0.80

    def test_tax_rate_below_minimum_raises_validation_error(self):
        with pytest.raises(ValidationError):
            EconomyState(tick=0, tax_rate=-0.01, items={}, agents={})

    def test_tax_rate_above_maximum_raises_validation_error(self):
        with pytest.raises(ValidationError):
            EconomyState(tick=0, tax_rate=0.81, items={}, agents={})


class TestPolicyRequestModels:
    """Tests Policy REST request validation models."""

    def test_policy_tax_request_valid(self):
        req = PolicyTaxRequest(tax_rate=0.25)
        assert req.tax_rate == 0.25

    def test_policy_tax_request_out_of_bounds(self):
        with pytest.raises(ValidationError):
            PolicyTaxRequest(tax_rate=0.85)
        with pytest.raises(ValidationError):
            PolicyTaxRequest(tax_rate=-0.10)

    def test_policy_event_request_valid(self):
        req1 = PolicyEventRequest(event="Dragon Attack")
        assert req1.event == "Dragon Attack"
        req2 = PolicyEventRequest(event="Gold Rush")
        assert req2.event == "Gold Rush"
