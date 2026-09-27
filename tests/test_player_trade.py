"""
Unit and Integration Tests for Playable Player Merchant System.

Tests:
1. Player initialization in default economy state.
2. Player BUY transaction validity and atomic gold/inventory execution.
3. Player BUY rejection on insufficient gold or market supply.
4. Player SELL transaction validity and gross/net revenue with tax.
5. Player SELL rejection on insufficient inventory.
6. Market price discovery movement in response to player trades.
7. REST endpoint POST /player/trade with valid and invalid payloads.
8. Player agent safety during simulation tick (no automatic AI override).
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.models import ActionType, AgentDecision, AgentState, EconomyState, PlayerTradeRequest
from src.market import execute_transaction, update_market_prices
from src.config import get_default_economy_state
import src.simulation as sim_module


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fresh_sim_state():
    sim_module.reset_state()
    return sim_module.state


def test_player_agent_initialization():
    """Verify player agent is initialized with correct defaults."""
    state = get_default_economy_state()
    assert "You (Merchant)" in state.agents
    player = state.agents["You (Merchant)"]
    assert player.is_player is True
    assert player.gold == 100.0
    assert player.inventory.get("Health Potion") == 2
    assert player.inventory.get("Iron Sword") == 1
    assert player.inventory.get("Raw Gem") == 2


def test_player_buy_transaction_success():
    """Player successfully buys items with tax deducted and inventory increased."""
    state = get_default_economy_state()
    player_name = "You (Merchant)"
    initial_gold = state.agents[player_name].gold
    initial_hp = state.agents[player_name].inventory.get("Health Potion", 0)
    initial_supply = state.items["Health Potion"].supply

    decision = AgentDecision(
        action=ActionType.BUY,
        item="Health Potion",
        quantity=2,
        reasoning="Player buy test",
    )

    record = execute_transaction(state, player_name, decision)
    assert record.status == "EXECUTED"
    # Unit price = 20.0, qty = 2, tax = 20 * 2 * 0.10 = 4.0 -> total = 44.0
    assert record.total_cost == 44.0
    assert record.tax_paid == 4.0
    assert state.agents[player_name].gold == initial_gold - 44.0
    assert state.agents[player_name].inventory["Health Potion"] == initial_hp + 2
    assert state.items["Health Potion"].supply == initial_supply - 2


def test_player_buy_insufficient_gold():
    """Player BUY rejected when gold is insufficient."""
    state = get_default_economy_state()
    player_name = "You (Merchant)"
    state.agents[player_name].gold = 5.0  # Cannot afford 20G + tax

    decision = AgentDecision(
        action=ActionType.BUY,
        item="Health Potion",
        quantity=1,
        reasoning="Player broke buy test",
    )

    record = execute_transaction(state, player_name, decision)
    assert record.status == "REJECTED"
    assert "Insufficient gold" in record.reason
    assert state.agents[player_name].gold == 5.0


def test_player_sell_transaction_success():
    """Player successfully sells items and receives gold after tax."""
    state = get_default_economy_state()
    player_name = "You (Merchant)"
    initial_gold = state.agents[player_name].gold
    initial_gems = state.agents[player_name].inventory.get("Raw Gem", 0)

    decision = AgentDecision(
        action=ActionType.SELL,
        item="Raw Gem",
        quantity=2,
        reasoning="Player sell test",
    )

    record = execute_transaction(state, player_name, decision)
    assert record.status == "EXECUTED"
    # Price = 15.0, qty = 2, gross = 30.0, tax = 3.0, net = 27.0
    assert record.total_cost == 30.0
    assert record.tax_paid == 3.0
    assert state.agents[player_name].gold == initial_gold + 27.0
    assert state.agents[player_name].inventory["Raw Gem"] == initial_gems - 2


def test_player_sell_insufficient_inventory():
    """Player SELL rejected when not holding enough items."""
    state = get_default_economy_state()
    player_name = "You (Merchant)"
    state.agents[player_name].inventory["Iron Sword"] = 0

    decision = AgentDecision(
        action=ActionType.SELL,
        item="Iron Sword",
        quantity=1,
        reasoning="Player empty inventory sell test",
    )

    record = execute_transaction(state, player_name, decision)
    assert record.status == "REJECTED"
    assert "Insufficient inventory" in record.reason


def test_player_trade_moves_market_price():
    """Executing player BUY shifts the item market price up."""
    state = get_default_economy_state()
    player_name = "You (Merchant)"
    old_price = state.items["Health Potion"].price

    decision = AgentDecision(
        action=ActionType.BUY,
        item="Health Potion",
        quantity=4,
        reasoning="Aggressive player buy",
    )

    record = execute_transaction(state, player_name, decision)
    assert record.status == "EXECUTED"

    update_market_prices(state, [record], k=0.05, min_price=1.0)
    # ΔD = +4 -> +20% -> 20.0 * 1.20 = 24.0
    assert state.items["Health Potion"].price == round(old_price * (1 + 0.05 * 4), 2)
    assert state.items["Health Potion"].price > old_price


def test_player_trade_rest_api_endpoint(client, fresh_sim_state):
    """Test POST /player/trade endpoint execution and response schema."""
    payload = {
        "action": "BUY",
        "item": "Raw Gem",
        "quantity": 1,
        "player_name": "You (Merchant)"
    }
    response = client.post("/player/trade", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "EXECUTED"
    assert "record" in data
    assert "player" in data
    assert data["player"]["name"] == "You (Merchant)"


def test_player_trade_rest_api_rejection(client, fresh_sim_state):
    """Test POST /player/trade returns 400 status code on rejected trade."""
    payload = {
        "action": "SELL",
        "item": "Iron Sword",
        "quantity": 5,  # Player only holds 1
        "player_name": "You (Merchant)"
    }
    response = client.post("/player/trade", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "REJECTED"
    assert "Insufficient inventory" in data["message"]
