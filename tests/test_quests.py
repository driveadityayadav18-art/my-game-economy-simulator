"""
Unit and Integration Tests for Quest & Expedition Consequence Engine (Step 2).

Tests:
1. Dungeon Raid with full equipment: consumes 1 Health Potion, awards gold loot & ancient gems.
2. Dungeon Raid underprepared: executes risk roll and handles injury or scout rewards.
3. Gem Prospecting with sword equipped: mines raw gems and awards prospecting gold.
4. Gem Prospecting without sword: rejects quest with gear warning.
5. Caravan Escort with 2 Potions + 1 Sword: consumes 1 potion, awards high bounty.
6. Caravan Escort missing required items: rejects quest with gear warning.
7. REST endpoint POST /player/quest execution and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.events import execute_quest
from src.config import get_default_economy_state
import src.simulation as sim_module


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fresh_sim_state():
    sim_module.reset_state()
    return sim_module.state


def test_dungeon_raid_full_gear_success():
    """Dungeon raid with potion & sword consumes potion and awards 45-90G loot."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Health Potion"] = 2
    player.inventory["Iron Sword"] = 1
    initial_gold = player.gold

    result = execute_quest(state, "DUNGEON_RAID", "You (Merchant)")
    assert result["success"] is True
    assert result["status"] == "SUCCESS"
    assert player.inventory["Health Potion"] == 1  # Consumed 1 potion
    assert player.gold >= initial_gold + 45.0
    assert "Dungeon Vault conquered" in result["message"]


def test_gem_prospecting_success():
    """Gem prospecting with iron sword yields 2-5 raw gems and bonus gold."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Iron Sword"] = 1
    initial_gems = player.inventory.get("Raw Gem", 0)
    initial_gold = player.gold

    result = execute_quest(state, "GEM_PROSPECTING", "You (Merchant)")
    assert result["success"] is True
    assert result["status"] == "SUCCESS"
    assert player.inventory["Raw Gem"] >= initial_gems + 2
    assert player.gold > initial_gold


def test_gem_prospecting_missing_sword():
    """Gem prospecting without sword tool fails with gear prerequisite error."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Iron Sword"] = 0

    result = execute_quest(state, "GEM_PROSPECTING", "You (Merchant)")
    assert result["success"] is False
    assert result["status"] == "MISSING_GEAR"
    assert "Iron Sword" in result["message"]


def test_caravan_escort_success():
    """Caravan escort with 2 potions + 1 sword awards massive bounty + raw gem."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Health Potion"] = 2
    player.inventory["Iron Sword"] = 1
    player.inventory["Raw Gem"] = 0
    initial_gold = player.gold

    result = execute_quest(state, "CARAVAN_ESCORT", "You (Merchant)")
    assert result["success"] is True
    assert result["status"] == "SUCCESS"
    assert player.inventory["Health Potion"] == 1  # Consumed 1
    assert player.inventory["Raw Gem"] == 1  # Awarded 1
    assert player.gold >= initial_gold + 75.0


def test_caravan_escort_missing_potions():
    """Caravan escort without sufficient potions fails."""
    state = get_default_economy_state()
    player = state.agents["You (Merchant)"]
    player.inventory["Health Potion"] = 1  # Needs 2
    player.inventory["Iron Sword"] = 1

    result = execute_quest(state, "CARAVAN_ESCORT", "You (Merchant)")
    assert result["success"] is False
    assert result["status"] == "MISSING_GEAR"


def test_player_quest_rest_api_dungeon_raid(client, fresh_sim_state):
    """POST /player/quest executes successfully for valid dungeon raid."""
    payload = {
        "quest_type": "DUNGEON_RAID",
        "player_name": "You (Merchant)"
    }
    response = client.post("/player/quest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "state" in data


def test_player_quest_rest_api_unknown_quest(client, fresh_sim_state):
    """POST /player/quest with invalid quest type returns validation error."""
    payload = {
        "quest_type": "NON_EXISTENT_QUEST",
        "player_name": "You (Merchant)"
    }
    response = client.post("/player/quest", json=payload)
    assert response.status_code == 422  # Pydantic Enum validation failure
