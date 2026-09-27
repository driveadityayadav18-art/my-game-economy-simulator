"""
Unit and Integration Tests for Crafting & Supply Chain Engine (Step 3).

Tests:
1. Forging Enchanted Blade consumes 1 Sword + 1 Gem + 5.0G fee.
2. Brewing Greater Elixir consumes 1 Potion + 1 Gem + 5.0G fee.
3. Crafting failure on missing raw materials or insufficient fee.
4. REST endpoint POST /player/craft execution and validation.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.events import execute_craft
from src.config import get_default_economy_state
import src.simulation as sim_module


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fresh_sim_state():
    sim_module.reset_state()
    return sim_module.state


def test_forge_enchanted_blade_success():
    """Crafting Enchanted Blade deducts materials & fee and grants tier 2 item."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Iron Sword"] = 2
    player.inventory["Raw Gem"] = 2
    player.gold = 50.0

    result = execute_craft(state, "ENCHANTED_BLADE", quantity=1, agent_name="You (Merchant)")
    assert result["success"] is True
    assert result["status"] == "SUCCESS"
    assert player.inventory["Iron Sword"] == 1
    assert player.inventory["Raw Gem"] == 1
    assert player.gold == 45.0
    assert player.inventory["Enchanted Blade"] == 1


def test_brew_greater_elixir_success():
    """Brewing Greater Elixir deducts potion + gem + fee and grants elixir."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Health Potion"] = 2
    player.inventory["Raw Gem"] = 2
    player.gold = 50.0

    result = execute_craft(state, "GREATER_ELIXIR", quantity=1, agent_name="You (Merchant)")
    assert result["success"] is True
    assert result["status"] == "SUCCESS"
    assert player.inventory["Health Potion"] == 1
    assert player.inventory["Raw Gem"] == 1
    assert player.gold == 45.0
    assert player.inventory["Greater Elixir"] == 1


def test_crafting_missing_materials_rejected():
    """Crafting without raw materials returns clean error."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Iron Sword"] = 0
    player.inventory["Raw Gem"] = 0

    result = execute_craft(state, "ENCHANTED_BLADE", quantity=1, agent_name="You (Merchant)")
    assert result["success"] is False
    assert result["status"] == "MISSING_MATERIALS"


def test_crafting_insufficient_fee_rejected():
    """Crafting without enough gold for fee returns clean error."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Iron Sword"] = 1
    player.inventory["Raw Gem"] = 1
    player.gold = 1.0  # Needs 5.0G fee

    result = execute_craft(state, "ENCHANTED_BLADE", quantity=1, agent_name="You (Merchant)")
    assert result["success"] is False
    assert result["status"] == "MISSING_MATERIALS"


def test_player_craft_rest_api_endpoint(client, fresh_sim_state):
    """POST /player/craft executes forging over REST API."""
    payload = {
        "recipe": "ENCHANTED_BLADE",
        "quantity": 1,
        "player_name": "You (Merchant)"
    }
    response = client.post("/player/craft", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["item_crafted"] == "Enchanted Blade"
    assert "state" in data
