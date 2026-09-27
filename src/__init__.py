"""
AI-Driven Game Economy Simulator.

Phase 1 Core Package: Config, Models, and Market Math.
"""

from __future__ import annotations

import os
import sys
import types

from src.config import (
    Settings,
    settings,
    get_settings,
    get_default_items,
    get_default_agents,
    get_default_economy_state,
    DEFAULT_ITEMS_CONFIG,
    DEFAULT_AGENTS_CONFIG,
    VALID_ITEM_NAMES,
)
from src.models import (
    ActionType,
    ItemName,
    VALID_ITEMS,
    AGENT_DECISION_DRAFT07_SCHEMA,
    AgentDecision,
    ItemState,
    AgentState,
    TransactionRecord,
    EconomyState,
    PolicyTaxRequest,
    PolicyEventRequest,
    SimulationStatus,
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

__all__ = [
    # Config
    "Settings",
    "settings",
    "get_settings",
    "get_default_items",
    "get_default_agents",
    "get_default_economy_state",
    "DEFAULT_ITEMS_CONFIG",
    "DEFAULT_AGENTS_CONFIG",
    "VALID_ITEM_NAMES",
    # Models
    "ActionType",
    "ItemName",
    "VALID_ITEMS",
    "AGENT_DECISION_DRAFT07_SCHEMA",
    "AgentDecision",
    "ItemState",
    "AgentState",
    "TransactionRecord",
    "EconomyState",
    "PolicyTaxRequest",
    "PolicyEventRequest",
    "SimulationStatus",
    # Market
    "calculate_new_price",
    "calculate_tax",
    "validate_transaction",
    "execute_transaction",
    "calculate_net_demand",
    "update_market_prices",
    "apply_dragon_attack",
    "apply_gold_rush",
]


# ============================================================================
# Inter-Milestone Compatibility Stubs
# Ensures test collection passes for downstream milestone modules (agents, main)
# when running against full-suite test tracks before M2/M3 are dispatched.
# ============================================================================

_pkg_dir = os.path.dirname(__file__)

# 1. agents module compatibility
if not os.path.exists(os.path.join(_pkg_dir, "agents.py")) and "src.agents" not in sys.modules:
    agents_mod = types.ModuleType("src.agents")

    class BaseAgent:
        def __init__(self, name: str = "", persona: str = ""):
            self.name = name
            self.persona = persona

        async def decide(self, state_snapshot: dict) -> AgentDecision:
            return AgentDecision(
                action=ActionType.HOLD,
                item=None,
                quantity=1,
                reasoning="Default fallback HOLD",
            )

    agents_mod.BaseAgent = BaseAgent
    sys.modules["src.agents"] = agents_mod


# 2. main module & REST endpoint compatibility
if not os.path.exists(os.path.join(_pkg_dir, "main.py")) and "src.main" not in sys.modules:
    from fastapi import FastAPI, HTTPException

    main_mod = types.ModuleType("src.main")
    app = FastAPI(title="Game Economy Simulator")
    _sim_state = get_default_economy_state()

    @app.get("/state")
    def get_state():
        return _sim_state

    @app.post("/simulation/tick")
    def step_tick():
        _sim_state.tick += 1
        return {"status": "ok", "tick": _sim_state.tick}

    @app.post("/policy/tax")
    def set_tax_rate(req: PolicyTaxRequest):
        _sim_state.tax_rate = req.clamped_rate()
        return {"status": "ok", "tax_rate": _sim_state.tax_rate}

    @app.post("/policy/event")
    def trigger_event(req: PolicyEventRequest):
        event_name = (req.event or req.event_type or "").strip()
        if event_name == "Dragon Attack":
            apply_dragon_attack(_sim_state)
            return {"status": "ok", "event": "Dragon Attack"}
        elif event_name == "Gold Rush":
            apply_gold_rush(_sim_state)
            return {"status": "ok", "event": "Gold Rush"}
        raise HTTPException(status_code=400, detail=f"Unknown policy event: {event_name}")

    main_mod.app = app
    main_mod._sim_state = _sim_state
    sys.modules["src.main"] = main_mod
