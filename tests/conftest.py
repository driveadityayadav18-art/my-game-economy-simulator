import asyncio
import pytest
from typing import Dict, Any, Optional
from fastapi.testclient import TestClient

from src.models import (
    ActionType,
    AgentDecision,
    ItemState,
    AgentState,
    EconomyState,
    TransactionRecord,
    PolicyTaxRequest,
    PolicyEventRequest,
)


@pytest.fixture
def initial_items() -> Dict[str, ItemState]:
    """Returns baseline item states for testing."""
    return {
        "Health Potion": ItemState(name="Health Potion", price=20.0, supply=100),
        "Iron Sword": ItemState(name="Iron Sword", price=30.0, supply=100),
        "Raw Gem": ItemState(name="Raw Gem", price=15.0, supply=100),
    }


@pytest.fixture
def initial_agents() -> Dict[str, AgentState]:
    """Returns baseline persona agents with starting gold and inventories."""
    return {
        "Garrick the Greedy": AgentState(
            name="Garrick the Greedy",
            persona="Garrick the Greedy",
            gold=150.0,
            inventory={"Health Potion": 2, "Iron Sword": 1, "Raw Gem": 5},
            last_action=None,
        ),
        "Cora the Farmer": AgentState(
            name="Cora the Farmer",
            persona="Cora the Farmer",
            gold=60.0,
            inventory={"Health Potion": 2, "Iron Sword": 0, "Raw Gem": 10},
            last_action=None,
        ),
        "Boran the Adventurer": AgentState(
            name="Boran the Adventurer",
            persona="Boran the Adventurer",
            gold=40.0,
            inventory={"Health Potion": 1, "Iron Sword": 1, "Raw Gem": 0},
            last_action=None,
        ),
    }


@pytest.fixture
def fresh_economy_state(initial_items, initial_agents) -> EconomyState:
    """Returns a completely fresh, isolated EconomyState for test execution."""
    return EconomyState(
        tick=0,
        running=False,
        tax_rate=0.10,
        items=initial_items,
        agents=initial_agents,
        recent_transactions=[],
    )


@pytest.fixture
def test_client():
    """FastAPI TestClient instance connected to application entrypoint."""
    import src.simulation as sim_module
    sim_module.reset_state()
    from src.main import app
    return TestClient(app)


class MockLLMProvider:
    """Mock LLM engine that can simulate deterministic responses, latency delays, and failures."""
    
    def __init__(self):
        self.preset_response: Optional[dict] = None
        self.delay_seconds: float = 0.0
        self.should_fail: bool = False
        self.failure_exception: Exception = RuntimeError("Simulated LLM Provider Failure")

    def configure_response(self, action: str, item: Optional[str], quantity: int, reasoning: str):
        self.preset_response = {
            "action": action,
            "item": item,
            "quantity": quantity,
            "reasoning": reasoning,
        }
        self.should_fail = False

    def configure_delay(self, seconds: float):
        self.delay_seconds = seconds

    def configure_failure(self, exc: Optional[Exception] = None):
        self.should_fail = True
        if exc:
            self.failure_exception = exc

    async def generate_decision(self, prompt: str) -> dict:
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        if self.should_fail:
            raise self.failure_exception
        if self.preset_response:
            return self.preset_response
        return {
            "action": "HOLD",
            "item": None,
            "quantity": 1,
            "reasoning": "Mock default fallback HOLD",
        }


@pytest.fixture
def mock_llm() -> MockLLMProvider:
    return MockLLMProvider()


def assert_state_invariants(state: EconomyState) -> None:
    """Verifies that universal macroeconomic invariants hold true."""
    assert state.tick >= 0, f"Tick count must be non-negative, got {state.tick}"
    assert 0.0 <= state.tax_rate <= 0.80, f"Tax rate out of bounds [0.0, 0.80]: {state.tax_rate}"
    
    # Item invariants
    for item_name, item in state.items.items():
        assert item.price >= 1.0, f"Price floor violated for {item_name}: {item.price} < 1.0"
        assert item.supply >= 0, f"Negative supply for {item_name}: {item.supply}"
        assert round(item.price, 2) == item.price, f"Price precision drift on {item_name}: {item.price}"
        
    # Agent invariants
    for agent_name, agent in state.agents.items():
        assert agent.gold >= 0.0, f"Agent {agent_name} has negative gold: {agent.gold}"
        assert round(agent.gold, 2) == round(agent.gold, 4), f"Gold precision drift for {agent_name}: {agent.gold}"
        for item_name, qty in agent.inventory.items():
            assert qty >= 0, f"Negative inventory for {agent_name} [{item_name}]: {qty}"
