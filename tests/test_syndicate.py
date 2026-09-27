"""
Unit and Integration Tests for Shadow Syndicate & Underhanded Market Tactics (Step 4).

Tests:
1. Bandit Raid sabotages Cora's gems and spikes Raw Gem prices.
2. Bandit Raid fails when player has insufficient gold for mercenary fee.
3. Smuggle Run bypasses market taxes without paying government tariff.
4. Smuggle Run fails when player holds 0 units of contraband.
5. Cartel Monopoly bribes Garrick and surges Potion/Sword prices.
6. REST endpoint POST /player/syndicate execution and validation.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.events import execute_syndicate_op
from src.config import get_default_economy_state
import src.simulation as sim_module


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fresh_sim_state():
    sim_module.reset_state()
    return sim_module.state


def test_bandit_raid_success():
    """Bandit raid deducts 30G, cuts Cora's gems, and spikes gem market price."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    cora = state.agents["Cora the Farmer"]
    player.gold = 100.0
    cora_gems = cora.inventory["Raw Gem"]
    old_gem_price = state.items["Raw Gem"].price

    result = execute_syndicate_op(state, "BANDIT_RAID", None, "You (Merchant)")
    assert result["success"] is True
    assert result["status"] == "SUCCESS"
    assert player.gold == 70.0  # -30G fee
    assert cora.inventory["Raw Gem"] < cora_gems  # Raided
    assert state.items["Raw Gem"].price > old_gem_price  # Spiked


def test_bandit_raid_insufficient_funds():
    """Bandit raid fails if player lacks 30G fee."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.gold = 10.0

    result = execute_syndicate_op(state, "BANDIT_RAID", None, "You (Merchant)")
    assert result["success"] is False
    assert result["status"] == "INSUFFICIENT_FUNDS"


def test_smuggle_run_evades_tax(monkeypatch):
    """Smuggle run bypasses taxes when evade roll succeeds."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Raw Gem"] = 3
    player.gold = 100.0
    gem_price = state.items["Raw Gem"].price

    # Force evade roll (random < 0.25 -> False)
    monkeypatch.setattr("random.random", lambda: 0.99)

    result = execute_syndicate_op(state, "SMUGGLE_RUN", "Raw Gem", "You (Merchant)")
    assert result["success"] is True
    assert result["status"] == "SUCCESS"
    assert player.inventory["Raw Gem"] == 2
    assert player.gold == 100.0 + gem_price


def test_smuggle_run_missing_contraband():
    """Smuggle run fails when player holds 0 units."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Raw Gem"] = 0

    result = execute_syndicate_op(state, "SMUGGLE_RUN", "Raw Gem", "You (Merchant)")
    assert result["success"] is False
    assert result["status"] == "MISSING_CONTRABAND"


def test_cartel_price_fixing_success():
    """Cartel pact transfers 40G bribe to Garrick and spikes commodity prices."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    garrick = state.agents["Garrick the Greedy"]
    player.gold = 100.0
    garrick_gold = garrick.gold
    old_hp_price = state.items["Health Potion"].price

    result = execute_syndicate_op(state, "CARTEL_PRICE_FIX", None, "You (Merchant)")
    assert result["success"] is True
    assert result["status"] == "SUCCESS"
    assert player.gold == 60.0
    assert garrick.gold == garrick_gold + 40.0
    assert state.items["Health Potion"].price > old_hp_price


def test_player_syndicate_rest_api_endpoint(client, fresh_sim_state):
    """POST /player/syndicate executes sabotage operation over REST API."""
    payload = {
        "op_type": "BANDIT_RAID",
        "player_name": "You (Merchant)"
    }
    response = client.post("/player/syndicate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "state" in data
