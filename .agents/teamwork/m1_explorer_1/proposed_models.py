"""
Pydantic Data Models and Schema Definitions for Game Economy Simulator.

Defines schemas for agent decisions, market commodities, agent accounts,
transaction logs, macroeconomic policy controls, and complete simulation state.
Complies with Draft-07 JSON Schema specifications.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Action and Item Enums / Literals
# ============================================================================

class ActionType(str, Enum):
    """Supported agent economic actions."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CRAFT = "CRAFT"  # Fallback to HOLD in Phase 1


ItemName = Literal["Health Potion", "Iron Sword", "Raw Gem"]

VALID_ITEMS: tuple[str, ...] = ("Health Potion", "Iron Sword", "Raw Gem")


# ============================================================================
# Draft-07 JSON Schema Specification for LLM Structured Outputs
# ============================================================================

AGENT_DECISION_DRAFT07_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["BUY", "SELL", "CRAFT", "HOLD"],
        },
        "item": {
            "type": ["string", "null"],
            "enum": ["Health Potion", "Iron Sword", "Raw Gem", None],
        },
        "quantity": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
        },
        "reasoning": {
            "type": "string",
            "maxLength": 120,
        },
    },
    "required": ["action", "item", "quantity", "reasoning"],
}


# ============================================================================
# Core Domain Models
# ============================================================================

class AgentDecision(BaseModel):
    """
    Structured decision emitted by an autonomous persona agent each tick.
    Validates strictly against Draft-07 constraints (quantity 1..10, reasoning <= 120).
    """
    action: ActionType
    item: Optional[ItemName] = None
    quantity: int = Field(default=1, ge=1, le=10, description="Quantity to trade (1 to 10)")
    reasoning: str = Field(..., max_length=120, description="Persona economic rationale (max 120 chars)")

    model_config = {
        "json_schema_extra": AGENT_DECISION_DRAFT07_SCHEMA,
        "use_enum_values": True,
    }


class ItemState(BaseModel):
    """
    Current market price and available inventory supply for a commodity.
    Enforces minimum price floor of 1.0 Gold and non-negative supply.
    """
    name: str
    price: float = Field(..., ge=1.0, description="Current market price (>= 1.0 Gold)")
    supply: int = Field(default=100, ge=0, description="Units available in market inventory")

    @field_validator("price", mode="after")
    @classmethod
    def round_price(cls, v: float) -> float:
        return round(v, 2)


class AgentState(BaseModel):
    """
    Individual agent balance sheet and portfolio state.
    Enforces non-negative wealth and inventory invariants.
    """
    name: str
    persona: str
    gold: float = Field(..., ge=0.0, description="Agent gold balance (>= 0.0)")
    inventory: Dict[str, int] = Field(default_factory=dict, description="Inventory of commodities held")
    last_action: Optional[AgentDecision] = None

    @field_validator("gold", mode="after")
    @classmethod
    def round_gold(cls, v: float) -> float:
        return round(v, 2)

    @field_validator("inventory", mode="after")
    @classmethod
    def validate_inventory(cls, v: Dict[str, int]) -> Dict[str, int]:
        for item, count in v.items():
            if count < 0:
                raise ValueError(f"Inventory count for '{item}' cannot be negative: {count}")
        return v


class TransactionRecord(BaseModel):
    """
    Audit log record for an executed, rejected, or skipped transaction.
    """
    tick: int = Field(ge=0, description="Simulation tick index")
    agent_name: str
    action: ActionType
    item: Optional[str] = None
    quantity: int = Field(default=1, ge=0)
    unit_price: float = Field(default=0.0, ge=0.0)
    tax_paid: float = Field(default=0.0, ge=0.0)
    total_cost: float = Field(default=0.0, ge=0.0)
    status: Literal["EXECUTED", "REJECTED", "SKIPPED"]
    reason: Optional[str] = None

    @field_validator("unit_price", "tax_paid", "total_cost", mode="after")
    @classmethod
    def round_monetary(cls, v: float) -> float:
        return round(v, 2)

    model_config = {
        "use_enum_values": True,
    }


class EconomyState(BaseModel):
    """
    Complete in-memory macroeconomic state store snapshot.
    """
    tick: int = Field(default=0, ge=0, description="Simulation tick counter")
    running: bool = Field(default=False, description="Whether background tick loop is active")
    tax_rate: float = Field(default=0.10, ge=0.0, le=0.80, description="Macroeconomic tax rate [0.0, 0.80]")
    items: Dict[str, ItemState] = Field(default_factory=dict, description="Catalog of traded items")
    agents: Dict[str, AgentState] = Field(default_factory=dict, description="Active market agents")
    recent_transactions: List[TransactionRecord] = Field(default_factory=list, description="Recent audit log")

    @field_validator("tax_rate", mode="after")
    @classmethod
    def round_tax_rate(cls, v: float) -> float:
        return round(v, 4)


# ============================================================================
# REST API Request & Response Models
# ============================================================================

class PolicyTaxRequest(BaseModel):
    """
    Request payload for updating the central bank transaction tax rate.
    Accepts floats and provides clamping helper for range [0.0, 0.80].
    """
    tax_rate: float = Field(..., description="Target tax rate between 0.0 (0%) and 0.80 (80%)")

    def clamped_rate(self) -> float:
        """Returns tax rate strictly clamped within legal macroeconomic bounds [0.0, 0.80]."""
        return max(0.0, min(0.80, round(self.tax_rate, 4)))


class PolicyEventRequest(BaseModel):
    """
    Request payload for triggering macroeconomic shock events.
    Supports both 'event' and 'event_type' fields for maximum client compatibility.
    """
    event: Optional[str] = Field(default=None, description="Event name: 'Dragon Attack' or 'Gold Rush'")
    event_type: Optional[str] = Field(default=None, description="Alias for event name")

    @model_validator(mode="after")
    def populate_event_fields(self) -> "PolicyEventRequest":
        ev = self.event or self.event_type
        if not ev:
            raise ValueError("Must provide either 'event' or 'event_type'")
        self.event = ev
        self.event_type = ev
        return self


class SimulationStatus(BaseModel):
    """
    Status response payload for start, stop, and status endpoints.
    """
    running: bool
    tick: int = 0
    message: Optional[str] = None
