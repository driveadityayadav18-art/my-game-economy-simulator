"""
Autonomous Persona Agent Decision Module.

Handles LLM queries for all 3 persona agents (Garrick, Cora, Boran) with:
- Multi-provider support: OpenAI, Anthropic, Gemini (via .env config)
- Strict JSON schema enforcement via AgentDecision model
- asyncio.gather() parallel execution across all agents per tick
- Graceful heuristic fallback on timeout, missing API keys, or malformed responses
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, Dict, Optional

from src.config import settings
from src.models import ActionType, AgentDecision, AgentState, EconomyState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persona system prompts
# ---------------------------------------------------------------------------

PERSONA_SYSTEM_PROMPTS: Dict[str, str] = {
    "Garrick the Greedy": (
        "You are Garrick the Greedy, a cunning market speculator. "
        "You hoard rare items and gold. You BUY cheap items aggressively when prices are low "
        "and SELL high when prices spike. You maximise profit at all costs."
    ),
    "Cora the Farmer": (
        "You are Cora the Farmer, a steady and risk-averse producer. "
        "You prefer to SELL Raw Gems consistently to maintain a reliable income. "
        "You avoid debt and only BUY essentials when your stock is critically low."
    ),
    "Boran the Adventurer": (
        "You are Boran the Adventurer, an impulsive thrill-seeker. "
        "You BUY Health Potions and Iron Swords whenever you have gold. "
        "You spend freely and keep a low balance, preferring action over saving."
    ),
}

DECISION_FORMAT_INSTRUCTION = """
Respond with ONLY a single valid JSON object matching this schema exactly:
{
  "action": "BUY" | "SELL" | "HOLD",
  "item": "Health Potion" | "Iron Sword" | "Raw Gem" | null,
  "quantity": <integer 1-10>,
  "reasoning": "<max 120 chars explaining your decision>"
}
Do not include markdown, explanation, or any other text outside the JSON object.
"""


def _build_user_prompt(agent: AgentState, state: EconomyState) -> str:
    prices = {name: item.price for name, item in state.items.items()}
    supplies = {name: item.supply for name, item in state.items.items()}
    return (
        f"Current market state — Tick #{state.tick}, Tax rate: {state.tax_rate*100:.0f}%\n"
        f"Prices: {prices}\n"
        f"Market supply: {supplies}\n"
        f"Your gold: {agent.gold:.2f}\n"
        f"Your inventory: {agent.inventory}\n"
        "What is your trading decision this tick?"
    )


# ---------------------------------------------------------------------------
# LLM provider callers
# ---------------------------------------------------------------------------

async def _call_openai(system: str, user: str) -> str:
    import httpx
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.DEFAULT_LLM_MODEL or "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system + "\n" + DECISION_FORMAT_INSTRUCTION},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
        "max_tokens": 200,
    }
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_anthropic(system: str, user: str) -> str:
    import httpx
    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 200,
        "system": system + "\n" + DECISION_FORMAT_INSTRUCTION,
        "messages": [{"role": "user", "content": user}],
    }
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


async def _call_gemini(system: str, user: str) -> str:
    import httpx
    model = "gemini-2.5-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": system + "\n" + DECISION_FORMAT_INSTRUCTION + "\n\n" + user}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 300,
            "temperature": 0.7,
            "thinkingConfig": {
                "thinkingBudget": 0,
            },
        },
    }
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _parse_decision(raw: str) -> Optional[AgentDecision]:
    """Parse raw LLM text into AgentDecision, returning None on any failure."""
    try:
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
        return AgentDecision(**data)
    except Exception as exc:
        logger.warning("Failed to parse LLM decision: %s | raw=%r", exc, raw[:200])
        return None


# ---------------------------------------------------------------------------
# Heuristic simulated fallback
# ---------------------------------------------------------------------------

def _heuristic_decision(agent: AgentState, state: EconomyState) -> AgentDecision:
    """
    Persona-driven dynamic heuristic fallback.
    Each persona reacts dynamically to price deviations, inventory levels, and macro trends.
    """
    name = agent.name
    items = list(state.items.values())
    items_sorted_by_price = sorted(items, key=lambda i: i.price)

    # 1. Garrick the Greedy: Speculator & Arbitrageur
    if "Greedy" in name:
        # Base price anchors: Potion: 20G, Sword: 30G, Gem: 15G
        baselines = {"Health Potion": 20.0, "Iron Sword": 30.0, "Raw Gem": 15.0}

        # Look to sell overvalued holdings first for maximum profit
        for item in items:
            base = baselines.get(item.name, item.price)
            if item.price >= base * 1.10 and agent.inventory.get(item.name, 0) >= 1:
                qty = min(2, agent.inventory.get(item.name, 0))
                return AgentDecision(
                    action=ActionType.SELL,
                    item=item.name,  # type: ignore[arg-type]
                    quantity=qty,
                    reasoning=f"Garrick: selling {item.name} at {item.price:.1f}G to lock in market profit",
                )

        # Look to buy undervalued commodities
        for item in items_sorted_by_price:
            base = baselines.get(item.name, item.price)
            cost = item.price * 1 * (1 + state.tax_rate)
            if item.price <= base * 1.05 and item.supply >= 1 and agent.gold >= cost:
                qty = 2 if agent.gold >= cost * 2 and item.supply >= 2 else 1
                return AgentDecision(
                    action=ActionType.BUY,
                    item=item.name,  # type: ignore[arg-type]
                    quantity=qty,
                    reasoning=f"Garrick: buying {qty}x cheap {item.name} at {item.price:.1f}G for future flip",
                )

    # 2. Cora the Farmer: Supply Engine & Resource Producer
    elif "Farmer" in name:
        # Primary: Sell harvested Raw Gems into the market
        raw_gems = agent.inventory.get("Raw Gem", 0)
        if raw_gems >= 1:
            qty = min(3, raw_gems) if raw_gems >= 3 else 1
            return AgentDecision(
                action=ActionType.SELL,
                item="Raw Gem",
                quantity=qty,
                reasoning=f"Cora: selling {qty}x Raw Gems to sustain farming cashflow",
            )

        # Secondary: If liquid and low on emergency potions, buy 1 Health Potion
        potion_item = state.items.get("Health Potion")
        if potion_item and potion_item.supply >= 1 and agent.gold >= 50.0:
            cost = potion_item.price * (1 + state.tax_rate)
            if agent.gold >= cost and agent.inventory.get("Health Potion", 0) == 0:
                return AgentDecision(
                    action=ActionType.BUY,
                    item="Health Potion",
                    quantity=1,
                    reasoning="Cora: purchasing emergency Health Potion for farm safety",
                )

    # 3. Boran the Adventurer: Consumer & Combat Artisan
    elif "Adventurer" in name:
        potions = agent.inventory.get("Health Potion", 0)
        swords = agent.inventory.get("Iron Sword", 0)

        # Sell raw gems found in dungeons to fund combat gear
        if agent.inventory.get("Raw Gem", 0) >= 1:
            return AgentDecision(
                action=ActionType.SELL,
                item="Raw Gem",
                quantity=1,
                reasoning="Boran: liquidating dungeon raw gems to buy combat supplies",
            )

        # Priority 1: Ensure at least 1-2 Health Potions for raids
        potion_item = state.items.get("Health Potion")
        if potion_item and potion_item.supply >= 1 and potions < 3:
            cost = potion_item.price * (1 + state.tax_rate)
            if agent.gold >= cost:
                return AgentDecision(
                    action=ActionType.BUY,
                    item="Health Potion",
                    quantity=1,
                    reasoning="Boran: stocking Health Potion for upcoming dungeon raid",
                )

        # Priority 2: Buy Iron Sword if well-stocked on potions
        sword_item = state.items.get("Iron Sword")
        if sword_item and sword_item.supply >= 1:
            cost = sword_item.price * (1 + state.tax_rate)
            if agent.gold >= cost:
                return AgentDecision(
                    action=ActionType.BUY,
                    item="Iron Sword",
                    quantity=1,
                    reasoning="Boran: upgrading equipment with a new Iron Sword",
                )

    return AgentDecision(
        action=ActionType.HOLD,
        item=None,
        quantity=1,
        reasoning="Market conditions stable; reserving balance.",
    )


# ---------------------------------------------------------------------------
# Main per-agent query function
# ---------------------------------------------------------------------------

async def query_agent(agent: AgentState, state: EconomyState) -> AgentDecision:
    """
    Queries the configured LLM provider for an agent decision.
    Falls back to heuristic on any failure or timeout.
    If agent is a human player, returns HOLD to preserve position until player acts.
    """
    if getattr(agent, "is_player", False):
        return AgentDecision(
            action=ActionType.HOLD,
            item=None,
            quantity=1,
            reasoning="Player holding market position.",
        )

    system_prompt = PERSONA_SYSTEM_PROMPTS.get(agent.name, f"You are {agent.name}, a market trader.")
    user_prompt = _build_user_prompt(agent, state)
    provider = settings.LLM_PROVIDER.lower()

    # Determine if provider has a valid key
    has_key = {
        "openai": bool(settings.OPENAI_API_KEY),
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "gemini": bool(settings.GEMINI_API_KEY),
    }

    if provider == "simulated" or not has_key.get(provider, False):
        logger.debug("Agent %s: using simulated heuristic fallback (provider=%s)", agent.name, provider)
        return _heuristic_decision(agent, state)

    try:
        caller = {
            "openai": _call_openai,
            "anthropic": _call_anthropic,
            "gemini": _call_gemini,
        }.get(provider)

        if caller is None:
            raise ValueError(f"Unknown LLM provider: {provider}")

        raw = await asyncio.wait_for(
            caller(system_prompt, user_prompt),
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        decision = _parse_decision(raw)
        if decision is not None:
            return decision
        logger.warning("Agent %s: unparseable LLM response, falling back to heuristic", agent.name)
    except asyncio.TimeoutError:
        logger.warning("Agent %s: LLM timed out after %.1fs, falling back to heuristic", agent.name, settings.LLM_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning("Agent %s: LLM error (%s), falling back to heuristic", agent.name, exc)

    return _heuristic_decision(agent, state)


async def query_all_agents(state: EconomyState) -> Dict[str, AgentDecision]:
    """
    Queries all agents concurrently via asyncio.gather().
    Returns dict mapping agent_name -> AgentDecision.
    """
    agent_names = list(state.agents.keys())
    agents = [state.agents[n] for n in agent_names]
    decisions = await asyncio.gather(*[query_agent(a, state) for a in agents])
    return dict(zip(agent_names, decisions))


# ---------------------------------------------------------------------------
# BaseAgent: testable interface for per-agent persona decisions
# ---------------------------------------------------------------------------

class BaseAgent:
    """
    Simple interface class for per-agent LLM/heuristic decision making.
    Provides an async decide() method usable in tests and the simulation.
    """

    def __init__(self, name: str, persona: str) -> None:
        self.name = name
        self.persona = persona

    async def decide(self, state_snapshot: Any) -> AgentDecision:
        """
        Given a state snapshot (dict or EconomyState), returns an AgentDecision.
        Falls back to heuristic when state is incomplete/corrupt or LLM unavailable.
        """
        from src.config import get_default_economy_state

        # Build a minimal EconomyState from dict snapshot or use default
        if isinstance(state_snapshot, EconomyState):
            eco_state = state_snapshot
        elif isinstance(state_snapshot, dict) and "items" in state_snapshot and "agents" in state_snapshot:
            try:
                eco_state = EconomyState.model_validate(state_snapshot)
            except Exception:
                eco_state = get_default_economy_state()
        else:
            # Corrupted or minimal snapshot — use defaults
            eco_state = get_default_economy_state()

        # Ensure this agent exists in the state
        if self.name not in eco_state.agents:
            agent_state = AgentState(
                name=self.name,
                persona=self.persona,
                gold=100.0,
                inventory={"Health Potion": 1, "Iron Sword": 1, "Raw Gem": 3},
            )
            eco_state.agents[self.name] = agent_state

        agent_state = eco_state.agents[self.name]
        return await query_agent(agent_state, eco_state)

