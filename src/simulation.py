"""
Simulation Tick Loop and State Orchestration.

Runs the async background simulation loop, coordinates agent decisions,
executes market transactions, updates prices, and manages loop lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List

from src.agents import query_all_agents
from src.config import settings, get_default_economy_state
from src.market import execute_transaction, update_market_prices
from src.models import EconomyState, TransactionRecord
from src.anomaly import reset_anomaly_state
from src.events import process_agent_lifecycles, process_autonomous_events, reset_event_engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared singleton economy state
# ---------------------------------------------------------------------------

state: EconomyState = get_default_economy_state()

# Background task handle
_tick_task: asyncio.Task | None = None

MAX_RECENT_TRANSACTIONS = 50  # Keep last N records in state


# ---------------------------------------------------------------------------
# Single tick execution
# ---------------------------------------------------------------------------

async def run_tick() -> List[TransactionRecord]:
    """
    Executes one simulation tick:
    1. Query all agents in parallel for decisions.
    2. Execute each agent's transaction against state.
    3. Update market prices based on net demand.
    4. Increment tick counter.
    5. Trim transaction log.

    Returns list of TransactionRecord for this tick.
    """
    global state

    logger.info("=== Tick #%d starting ===", state.tick)

    # Step 1: get all decisions in parallel
    decisions = await query_all_agents(state)

    # Step 2: execute each transaction
    tick_records: List[TransactionRecord] = []
    for agent_name, decision in decisions.items():
        record = execute_transaction(state, agent_name, decision)
        tick_records.append(record)
        logger.debug(
            "  %s → %s %s x%d [%s]",
            agent_name,
            decision.action,
            decision.item or "-",
            decision.quantity,
            record.status,
        )

    # Step 3: update market prices based on this tick's trades
    update_market_prices(state, tick_records, k=settings.PRICE_SENSITIVITY_K, min_price=settings.PRICE_FLOOR)

    # Step 4: execute dynamic agent lifecycles (farming harvest, dungeon raids, interest)
    lifecycle_logs = process_agent_lifecycles(state)
    for log_msg in lifecycle_logs:
        logger.info("Lifecycle: %s", log_msg)

    # Step 5: check for autonomous stochastic world events
    world_event = process_autonomous_events(state)
    if world_event:
        logger.info("Autonomous World Event: %s", world_event.get("headline"))

    # Step 6: advance tick counter
    state.tick += 1

    # Step 7: trim transaction log
    all_records = state.recent_transactions
    if len(all_records) > MAX_RECENT_TRANSACTIONS:
        state.recent_transactions = all_records[-MAX_RECENT_TRANSACTIONS:]

    logger.info("=== Tick #%d complete — prices: %s ===", state.tick - 1,
                {k: v.price for k, v in state.items.items()})

    return tick_records


# ---------------------------------------------------------------------------
# Background loop lifecycle
# ---------------------------------------------------------------------------

async def _loop_runner() -> None:
    """Continuous background tick runner."""
    while state.running:
        try:
            await run_tick()
        except Exception as exc:
            logger.error("Tick loop error (continuing): %s", exc)
        await asyncio.sleep(settings.SIMULATION_TICK_INTERVAL)


def start_loop() -> bool:
    """
    Starts the background simulation loop.
    Returns True if loop started, False if already running.
    """
    global _tick_task, state

    if state.running:
        return False

    state.running = True
    _tick_task = asyncio.get_event_loop().create_task(_loop_runner())
    logger.info("Simulation loop started.")
    return True


def stop_loop() -> bool:
    """
    Stops the background simulation loop.
    Returns True if stopped, False if was not running.
    """
    global _tick_task, state

    if not state.running:
        return False

    state.running = False
    if _tick_task and not _tick_task.done():
        _tick_task.cancel()
    _tick_task = None
    logger.info("Simulation loop stopped.")
    return True


def reset_state() -> None:
    """Resets economy state to initial defaults and stops loop."""
    global state
    stop_loop()
    state = get_default_economy_state()
    reset_anomaly_state()
    reset_event_engine()
    logger.info("Economy state reset to defaults.")
