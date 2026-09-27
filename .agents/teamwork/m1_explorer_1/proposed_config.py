"""
Simulation Configuration and Environment Settings.

Manages environment variables, macroeconomic parameter knobs,
default item catalog definitions, and initial persona agent states
for the AI-Driven Game Economy Simulator.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load variables from local .env if present
load_dotenv()


class Settings(BaseModel):
    """
    Macroeconomic knobs, execution timeouts, and server configuration.
    Reads from environment variables with deterministic defaults.
    """

    # --- Simulation Loop Knobs ---
    SIMULATION_TICK_INTERVAL: float = Field(
        default_factory=lambda: float(os.getenv("SIMULATION_TICK_INTERVAL", "4.0")),
        ge=0.1,
        description="Duration of each simulation tick in seconds (default: 4.0s)",
    )
    LLM_TIMEOUT_SECONDS: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "2.0")),
        ge=0.1,
        description="Maximum timeout for agent LLM calls before fallback to HOLD (default: 2.0s)",
    )

    # --- Macroeconomic & Market Knobs ---
    DEFAULT_TAX_RATE: float = Field(
        default_factory=lambda: float(os.getenv("DEFAULT_TAX_RATE", "0.10")),
        ge=0.0,
        le=0.80,
        description="Default transaction tax rate (default: 0.10, i.e. 10%)",
    )
    MIN_TAX_RATE: float = Field(
        default_factory=lambda: float(os.getenv("MIN_TAX_RATE", "0.0")),
        ge=0.0,
        description="Macroeconomic minimum tax floor (0.0%)",
    )
    MAX_TAX_RATE: float = Field(
        default_factory=lambda: float(os.getenv("MAX_TAX_RATE", "0.80")),
        le=1.0,
        description="Macroeconomic maximum tax ceiling (80.0%)",
    )
    PRICE_SENSITIVITY_K: float = Field(
        default_factory=lambda: float(os.getenv("PRICE_SENSITIVITY_K", "0.05")),
        ge=0.0,
        description="Sensitivity coefficient k in price discovery formula (default: 0.05)",
    )
    PRICE_FLOOR: float = Field(
        default_factory=lambda: float(os.getenv("PRICE_FLOOR", "1.0")),
        ge=0.01,
        description="Absolute minimum price floor in Gold (default: 1.0 Gold)",
    )

    # --- LLM Provider Settings ---
    OPENAI_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY"),
        description="OpenAI API key",
    )
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"),
        description="Anthropic Claude API key",
    )
    GEMINI_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY"),
        description="Google Gemini API key",
    )
    LLM_PROVIDER: str = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "simulated"),
        description="Active LLM provider: openai, anthropic, gemini, or simulated",
    )
    DEFAULT_LLM_MODEL: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini"),
        description="Default model name for LLM queries",
    )

    # --- Server Settings ---
    HOST: str = Field(
        default_factory=lambda: os.getenv("HOST", "0.0.0.0"),
        description="FastAPI bind host",
    )
    PORT: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8000")),
        description="FastAPI bind port",
    )

    model_config = {
        "extra": "ignore",
    }


# Singleton configuration instance
settings = Settings()


# ============================================================================
# Default Market Catalog Definitions
# ============================================================================

DEFAULT_ITEMS_CONFIG: Dict[str, Dict[str, Any]] = {
    "Health Potion": {
        "price": 20.0,
        "supply": 100,
    },
    "Iron Sword": {
        "price": 30.0,
        "supply": 100,
    },
    "Raw Gem": {
        "price": 15.0,
        "supply": 100,
    },
}

VALID_ITEM_NAMES: Tuple[str, ...] = tuple(DEFAULT_ITEMS_CONFIG.keys())


# ============================================================================
# Default Agent Personas & Starting State Definitions
# ============================================================================

DEFAULT_AGENTS_CONFIG: Dict[str, Dict[str, Any]] = {
    "Garrick the Greedy": {
        "persona": "Garrick the Greedy: Hoards rare items and gold; buys low, sells high aggressively.",
        "gold": 150.0,
        "inventory": {
            "Health Potion": 2,
            "Iron Sword": 1,
            "Raw Gem": 5,
        },
    },
    "Cora the Farmer": {
        "persona": "Cora the Farmer: Prioritizes steady income; sells raw materials consistently, avoids debt/risk.",
        "gold": 60.0,
        "inventory": {
            "Health Potion": 2,
            "Iron Sword": 0,
            "Raw Gem": 10,
        },
    },
    "Boran the Adventurer": {
        "persona": "Boran the Adventurer: Prioritizes immediate consumption; spends gold on potions/weapons, maintains low balance.",
        "gold": 40.0,
        "inventory": {
            "Health Potion": 1,
            "Iron Sword": 1,
            "Raw Gem": 0,
        },
    },
}


# ============================================================================
# State Factory Helpers
# ============================================================================

def get_default_items() -> Dict[str, Any]:
    """
    Constructs a dictionary of initial ItemState models.
    Lazy imports models to prevent circular dependencies.
    """
    from src.models import ItemState

    return {
        name: ItemState(name=name, price=data["price"], supply=data["supply"])
        for name, data in DEFAULT_ITEMS_CONFIG.items()
    }


def get_default_agents() -> Dict[str, Any]:
    """
    Constructs a dictionary of initial AgentState models.
    Lazy imports models to prevent circular dependencies.
    """
    from src.models import AgentState

    return {
        name: AgentState(
            name=name,
            persona=data["persona"],
            gold=data["gold"],
            inventory=dict(data["inventory"]),
            last_action=None,
        )
        for name, data in DEFAULT_AGENTS_CONFIG.items()
    }


def get_default_economy_state() -> Any:
    """
    Constructs a fresh EconomyState seeded with default items, agents, and tax rate.
    Lazy imports models to prevent circular dependencies.
    """
    from src.models import EconomyState

    return EconomyState(
        tick=0,
        running=False,
        tax_rate=settings.DEFAULT_TAX_RATE,
        items=get_default_items(),
        agents=get_default_agents(),
        recent_transactions=[],
    )
