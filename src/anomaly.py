"""
Phase 3: Rule-Based Anomaly Detection & LLM News Alert Generator.

Detects market spikes, crashes, and wealth imbalances each tick.
Optionally generates LLM news headlines during economic crises.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from src.models import EconomyState

logger = logging.getLogger(__name__)

# Thresholds
SPIKE_THRESHOLD = 1.20    # Price increased ≥20% from baseline
CRASH_THRESHOLD = 0.80    # Price dropped ≤80% of baseline (≥20% drop)
WEALTH_SKEW_THRESHOLD = 3.0  # Richest agent has 3x more gold than poorest

# Store last-tick prices for delta comparison (module-level)
_prev_prices: Dict[str, float] = {}


def check_anomalies(state: EconomyState) -> List[Dict[str, Any]]:
    """
    Runs anomaly detection rules on current EconomyState.
    Returns a list of anomaly event dicts (empty if none detected).
    """
    global _prev_prices
    anomalies: List[Dict[str, Any]] = []

    for item_name, item in state.items.items():
        prev = _prev_prices.get(item_name, item.price)
        current = item.price

        if prev > 0:
            ratio = current / prev
            if ratio >= SPIKE_THRESHOLD:
                pct = (ratio - 1) * 100
                anomaly = {
                    "type": "SPIKE",
                    "item": item_name,
                    "prev_price": round(prev, 2),
                    "current_price": round(current, 2),
                    "change_pct": round(pct, 1),
                    "headline": _spike_headline(item_name, current, pct),
                }
                anomalies.append(anomaly)
                logger.warning("ANOMALY SPIKE: %s +%.1f%%", item_name, pct)

            elif ratio <= CRASH_THRESHOLD:
                pct = (1 - ratio) * 100
                anomaly = {
                    "type": "CRASH",
                    "item": item_name,
                    "prev_price": round(prev, 2),
                    "current_price": round(current, 2),
                    "change_pct": round(-pct, 1),
                    "headline": _crash_headline(item_name, current, pct),
                }
                anomalies.append(anomaly)
                logger.warning("ANOMALY CRASH: %s -%.1f%%", item_name, pct)

    # Wealth skew check
    gold_balances = [a.gold for a in state.agents.values() if a.gold > 0]
    if len(gold_balances) >= 2:
        ratio = max(gold_balances) / max(min(gold_balances), 0.01)
        if ratio >= WEALTH_SKEW_THRESHOLD:
            richest = max(state.agents.values(), key=lambda a: a.gold)
            anomalies.append({
                "type": "WEALTH_SKEW",
                "item": None,
                "richest_agent": richest.name,
                "gold_ratio": round(ratio, 2),
                "headline": f"🏦 MARKET ALERT: {richest.name} controls {ratio:.1f}x more wealth than rivals! Monopoly forming.",
            })

    # Update prev prices for next tick
    _prev_prices = {name: item.price for name, item in state.items.items()}

    return anomalies


def reset_anomaly_state():
    """Reset previous price tracking (call on sim reset)."""
    global _prev_prices
    _prev_prices = {}


# ---------------------------------------------------------------------------
# Headline generators (deterministic, no LLM needed for hackathon speed)
# ---------------------------------------------------------------------------

_SPIKE_TEMPLATES = [
    "🔥 BREAKING: {item} prices SURGE {pct:.0f}%! Traders scramble as supply collapses. Now at {price:.1f}G.",
    "📈 MARKET SHOCK: {item} skyrockets to {price:.1f}G (+{pct:.0f}%). Panic buying reported across all districts.",
    "⚡ CRISIS ALERT: {item} hits {price:.1f}G — a {pct:.0f}% spike in one tick! Central Bank watching closely.",
]

_CRASH_TEMPLATES = [
    "📉 CRASH: {item} collapses to {price:.1f}G, down {pct:.0f}%! Sellers flood the market.",
    "💀 MARKET BLOODBATH: {item} dumps {pct:.0f}%. Now at {price:.1f}G — is this the bottom?",
    "🚨 EMERGENCY: {item} in freefall at {price:.1f}G, -{pct:.0f}% this tick. Agents HOLDing positions.",
]

import random

def _spike_headline(item: str, price: float, pct: float) -> str:
    tpl = random.choice(_SPIKE_TEMPLATES)
    return tpl.format(item=item, price=price, pct=pct)

def _crash_headline(item: str, price: float, pct: float) -> str:
    tpl = random.choice(_CRASH_TEMPLATES)
    return tpl.format(item=item, price=price, pct=pct)
