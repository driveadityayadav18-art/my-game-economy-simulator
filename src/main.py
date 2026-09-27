"""
FastAPI Application Entry Point — AI-Driven Game Economy Simulator.

Exposes:
  GET  /health                — Healthcheck
  GET  /state                 — Full economy snapshot
  POST /simulation/tick       — Manual single tick
  POST /simulation/start      — Start background tick loop
  POST /simulation/stop       — Stop background tick loop
  POST /policy/tax            — Update tax rate
  POST /policy/event          — Trigger economic shock event
  WS   /ws                    — Real-time WebSocket state stream
  GET  /                      — Serve dashboard UI (index.html)
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Set

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pathlib import Path

from src.models import (
    EconomyState,
    PolicyEventRequest,
    PolicyTaxRequest,
    SimulationStatus,
    PlayerTradeRequest,
    QuestRequest,
    QuestType,
    CraftRequest,
    CraftRecipe,
    SyndicateRequest,
    SyndicateOpType,
    AgentDecision,
    AgentState,
    ActionType,
)
from src.market import (
    apply_dragon_attack,
    apply_gold_rush,
    apply_trade_war,
    apply_market_crash,
    apply_black_market,
    execute_transaction,
    update_market_prices,
)
from src.anomaly import check_anomalies
from src.events import (
    calculate_market_sentiment,
    evaluate_challenges,
    execute_quest,
    execute_craft,
    execute_syndicate_op,
)
from src.config import settings
import src.simulation as sim_module


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        logger.info("WS client connected. Total: %d", len(self.active))

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        logger.info("WS client disconnected. Total: %d", len(self.active))

    async def broadcast(self, data: dict):
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.active -= dead


manager = ConnectionManager()

# Patch simulation run_tick to broadcast after each tick
_original_run_tick = sim_module.run_tick

async def _run_tick_with_broadcast():
    records = await _original_run_tick()
    # Also check for anomalies and attach to broadcast
    anomalies = check_anomalies(sim_module.state)
    payload = _state_snapshot()
    payload["anomalies"] = anomalies
    await manager.broadcast(payload)
    return records

sim_module.run_tick = _run_tick_with_broadcast


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Game Economy Simulator starting up.")
    yield
    sim_module.stop_loop()
    logger.info("Simulator shut down cleanly.")


app = FastAPI(
    title="AI-Driven Game Economy Simulator",
    description="Phase 1+2+3 — Multi-Agent Economic Simulation Engine with Live Dashboard",
    version="2.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state_snapshot() -> Dict[str, Any]:
    """Serialise current EconomyState to a JSON-compatible dict."""
    state = sim_module.state
    return {
        "tick": state.tick,
        "running": state.running,
        "tax_rate": state.tax_rate,
        "items": {
            name: {"name": name, "price": item.price, "supply": item.supply}
            for name, item in state.items.items()
        },
        "agents": {
            name: {
                "name": name,
                "persona": agent.persona,
                "gold": agent.gold,
                "inventory": agent.inventory,
                "last_action": agent.last_action.model_dump() if agent.last_action else None,
            }
            for name, agent in state.agents.items()
        },
        "recent_transactions": [
            t.model_dump() for t in state.recent_transactions[-20:]
        ],
        "sentiment": calculate_market_sentiment(state),
        "challenges": evaluate_challenges(state),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "service": "game-economy-simulator"}


@app.get("/")
async def serve_dashboard():
    """Serve the Game Master dashboard UI."""
    ui_path = Path(__file__).parent / "index.html"
    if ui_path.exists():
        return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))
    return JSONResponse({"error": "Dashboard not found. Run the server from project root."}, status_code=404)


@app.get("/state")
async def get_state() -> JSONResponse:
    """Returns the complete current economy snapshot."""
    return JSONResponse(content=_state_snapshot())


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Real-time state streaming via WebSocket."""
    await manager.connect(ws)
    # Send immediate state snapshot on connect
    try:
        payload = _state_snapshot()
        payload["anomalies"] = check_anomalies(sim_module.state)
        await ws.send_json(payload)
        # Listen for incoming policy messages from client
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                msg = json.loads(data)
                await _handle_ws_message(msg)
            except asyncio.TimeoutError:
                # Send ping to keep alive
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as exc:
        logger.error("WS error: %s", exc)
        manager.disconnect(ws)


async def _handle_ws_message(msg: dict):
    """Handle incoming policy commands from the dashboard over WebSocket."""
    action = msg.get("action")
    if action == "set_tax":
        rate = float(msg.get("tax_rate", sim_module.state.tax_rate))
        sim_module.state.tax_rate = max(0.0, min(0.80, round(rate, 4)))
        logger.info("WS: Tax rate set to %.2f%%", sim_module.state.tax_rate * 100)
    elif action == "trigger_event":
        event = msg.get("event", "").lower()
        if "dragon" in event:
            apply_dragon_attack(sim_module.state)
            logger.info("WS: Dragon Attack triggered")
        elif "gold" in event:
            apply_gold_rush(sim_module.state)
            logger.info("WS: Gold Rush triggered")
        elif "trade" in event:
            apply_trade_war(sim_module.state)
            logger.info("WS: Trade War triggered")
        elif "crash" in event:
            apply_market_crash(sim_module.state)
            logger.info("WS: Market Crash triggered")
        elif "black" in event:
            apply_black_market(sim_module.state)
            logger.info("WS: Black Market triggered")
    elif action == "start":
        sim_module.start_loop()
    elif action == "stop":
        sim_module.stop_loop()
    elif action == "set_speed":
        interval = float(msg.get("interval", 4.0))
        # Clamp between 0.5s (fast demo) and 10s (slow)
        settings.SIMULATION_TICK_INTERVAL = max(0.5, min(10.0, round(interval, 1)))
        logger.info("WS: Tick speed set to %.1fs", settings.SIMULATION_TICK_INTERVAL)
    elif action == "player_trade":
        player_name = msg.get("player_name", "You (Merchant)")
        item = msg.get("item")
        trade_act = msg.get("trade_action", "BUY").upper()
        quantity = max(1, min(100, int(msg.get("quantity", 1))))

        if player_name not in sim_module.state.agents:
            sim_module.state.agents[player_name] = AgentState(
                name=player_name,
                persona="Player Merchant: Autonomous market participant.",
                gold=100.0,
                inventory={"Health Potion": 2, "Iron Sword": 1, "Raw Gem": 2},
                is_player=True,
            )

        decision = AgentDecision(
            action=ActionType(trade_act),
            item=item,
            quantity=quantity,
            reasoning=f"Player manual {trade_act} {quantity}x {item}",
        )
        record = execute_transaction(sim_module.state, player_name, decision)
        if record.status == "EXECUTED":
            update_market_prices(
                sim_module.state,
                [record],
                k=settings.PRICE_SENSITIVITY_K,
                min_price=settings.PRICE_FLOOR,
            )

        anomalies = check_anomalies(sim_module.state)
        payload = _state_snapshot()
        payload["anomalies"] = anomalies
        payload["player_trade_result"] = record.model_dump()
        await manager.broadcast(payload)
    elif action == "player_quest":
        player_name = msg.get("player_name", "You (Merchant)")
        quest_type = msg.get("quest_type", "DUNGEON_RAID")
        result = execute_quest(sim_module.state, quest_type, player_name)
        anomalies = check_anomalies(sim_module.state)
        payload = _state_snapshot()
        payload["anomalies"] = anomalies
        payload["quest_result"] = result
        await manager.broadcast(payload)
    elif action == "player_craft":
        player_name = msg.get("player_name", "You (Merchant)")
        recipe = msg.get("recipe", "ENCHANTED_BLADE")
        qty = int(msg.get("quantity", 1))
        result = execute_craft(sim_module.state, recipe, qty, player_name)
        anomalies = check_anomalies(sim_module.state)
        payload = _state_snapshot()
        payload["anomalies"] = anomalies
        payload["craft_result"] = result
        await manager.broadcast(payload)
    elif action == "player_syndicate":
        player_name = msg.get("player_name", "You (Merchant)")
        op_type = msg.get("op_type", "BANDIT_RAID")
        item = msg.get("item", "Raw Gem")
        result = execute_syndicate_op(sim_module.state, op_type, item, player_name)
        anomalies = check_anomalies(sim_module.state)
        payload = _state_snapshot()
        payload["anomalies"] = anomalies
        payload["syndicate_result"] = result
        await manager.broadcast(payload)


@app.post("/simulation/tick")
async def manual_tick() -> JSONResponse:
    """Steps a single simulation tick manually."""
    records = await sim_module.run_tick()
    return JSONResponse(content={
        "message": f"Tick #{sim_module.state.tick - 1} completed.",
        "transactions": [r.model_dump() for r in records],
        "state": _state_snapshot(),
    })


@app.post("/simulation/start", response_model=SimulationStatus)
async def start_simulation() -> SimulationStatus:
    """Starts the continuous background tick loop."""
    started = sim_module.start_loop()
    return SimulationStatus(
        running=sim_module.state.running,
        tick=sim_module.state.tick,
        message="Simulation loop started." if started else "Loop already running.",
    )


@app.post("/simulation/stop", response_model=SimulationStatus)
async def stop_simulation() -> SimulationStatus:
    """Stops the background tick loop."""
    stopped = sim_module.stop_loop()
    return SimulationStatus(
        running=sim_module.state.running,
        tick=sim_module.state.tick,
        message="Simulation loop stopped." if stopped else "Loop was not running.",
    )


@app.post("/simulation/reset", response_model=SimulationStatus)
async def reset_simulation() -> SimulationStatus:
    """Resets economy to initial defaults: stops loop, tick → 0, agents/prices restored."""
    sim_module.reset_state()
    return SimulationStatus(
        running=sim_module.state.running,
        tick=sim_module.state.tick,
        message="Economy reset to initial defaults.",
    )


@app.post("/policy/tax", response_model=SimulationStatus)
async def update_tax(body: PolicyTaxRequest) -> SimulationStatus:
    """Updates the economy-wide transaction tax rate (0% – 80%)."""
    new_rate = body.clamped_rate()
    sim_module.state.tax_rate = new_rate
    logger.info("Tax rate updated to %.2f%%", new_rate * 100)
    return SimulationStatus(
        running=sim_module.state.running,
        tick=sim_module.state.tick,
        message=f"Tax rate set to {new_rate * 100:.1f}%.",
    )


@app.post("/policy/event", response_model=SimulationStatus)
async def trigger_event(body: PolicyEventRequest) -> SimulationStatus:
    """Triggers an economic shock event: Dragon Attack, Gold Rush, Trade War, Market Crash, or Black Market."""
    event = (body.event or "").strip().lower()

    if event in ("dragon attack", "dragon_attack"):
        apply_dragon_attack(sim_module.state)
        msg = "Dragon Attack! Health Potion supply crashed to 2 and price spiked to 35 Gold."
        logger.info(msg)
    elif event in ("gold rush", "gold_rush"):
        apply_gold_rush(sim_module.state)
        msg = "Gold Rush! All agents received +100 Gold."
        logger.info(msg)
    elif event in ("trade war", "trade_war"):
        apply_trade_war(sim_module.state)
        msg = "Trade War! Tax rate surged to 50%. Trade activity will freeze."
        logger.info(msg)
    elif event in ("market crash", "market_crash"):
        apply_market_crash(sim_module.state)
        msg = "Market Crash! All prices dropped 40%. Bargain hunters incoming."
        logger.info(msg)
    elif event in ("black market", "black_market"):
        apply_black_market(sim_module.state)
        msg = "Black Market Surge! Prices spiked 25% and a lucky agent got +150 Gold."
        logger.info(msg)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event '{body.event}'. Valid: 'Dragon Attack', 'Gold Rush', 'Trade War', 'Market Crash', 'Black Market'.",
        )

    return SimulationStatus(
        running=sim_module.state.running,
        tick=sim_module.state.tick,
        message=msg,
    )


@app.post("/player/trade")
async def player_trade_endpoint(body: PlayerTradeRequest) -> JSONResponse:
    """
    Executes an immediate market transaction on behalf of the human player.
    Updates agent balance, market supply, prices, and broadcasts new state.
    """
    player_name = body.player_name or "You (Merchant)"
    if player_name not in sim_module.state.agents:
        sim_module.state.agents[player_name] = AgentState(
            name=player_name,
            persona="Player Merchant: Autonomous market participant seeking wealth and market control.",
            gold=100.0,
            inventory={"Health Potion": 2, "Iron Sword": 1, "Raw Gem": 2},
            is_player=True,
        )

    decision = AgentDecision(
        action=body.action,
        item=body.item,
        quantity=body.quantity,
        reasoning=f"Player manual {body.action.value} order for {body.quantity}x {body.item}",
    )

    record = execute_transaction(sim_module.state, player_name, decision)

    if record.status == "EXECUTED":
        update_market_prices(
            sim_module.state,
            [record],
            k=settings.PRICE_SENSITIVITY_K,
            min_price=settings.PRICE_FLOOR,
        )

    anomalies = check_anomalies(sim_module.state)
    payload = _state_snapshot()
    payload["anomalies"] = anomalies
    payload["player_trade_result"] = record.model_dump()
    await manager.broadcast(payload)

    status_code = 200 if record.status == "EXECUTED" else 400
    return JSONResponse(
        content={
            "status": record.status,
            "message": record.reason or f"Trade {record.status}",
            "record": record.model_dump(),
            "player": sim_module.state.agents[player_name].model_dump(),
            "state": _state_snapshot(),
        },
        status_code=status_code,
    )


@app.post("/player/quest")
async def player_quest_endpoint(body: QuestRequest) -> JSONResponse:
    """
    Executes a high-stakes adventure, prospecting, or caravan escort contract for the player.
    Consumes required gear, computes loot rewards or injury penalties, and broadcasts.
    """
    player_name = body.player_name or "You (Merchant)"
    if player_name not in sim_module.state.agents:
        sim_module.state.agents[player_name] = AgentState(
            name=player_name,
            persona="Player Merchant: Autonomous market participant seeking wealth and market control.",
            gold=100.0,
            inventory={"Health Potion": 2, "Iron Sword": 1, "Raw Gem": 2},
            is_player=True,
        )

    result = execute_quest(sim_module.state, body.quest_type.value, player_name)

    anomalies = check_anomalies(sim_module.state)
    payload = _state_snapshot()
    payload["anomalies"] = anomalies
    payload["quest_result"] = result
    await manager.broadcast(payload)

    status_code = 200 if result.get("success", False) else 400
    return JSONResponse(
        content={
            **result,
            "state": _state_snapshot(),
        },
        status_code=status_code,
    )


@app.post("/player/craft")
async def player_craft_endpoint(body: CraftRequest) -> JSONResponse:
    """
    Executes alchemy or blacksmith forging of advanced goods for the player.
    Consumes raw materials & forge fees, and adds manufactured goods to inventory.
    """
    player_name = body.player_name or "You (Merchant)"
    if player_name not in sim_module.state.agents:
        sim_module.state.agents[player_name] = AgentState(
            name=player_name,
            persona="Player Merchant: Autonomous market participant seeking wealth and market control.",
            gold=100.0,
            inventory={"Health Potion": 2, "Iron Sword": 1, "Raw Gem": 2},
            is_player=True,
        )

    result = execute_craft(sim_module.state, body.recipe.value, body.quantity, player_name)

    anomalies = check_anomalies(sim_module.state)
    payload = _state_snapshot()
    payload["anomalies"] = anomalies
    payload["craft_result"] = result
    await manager.broadcast(payload)

    status_code = 200 if result.get("success", False) else 400
    return JSONResponse(
        content={
            **result,
            "state": _state_snapshot(),
        },
        status_code=status_code,
    )


@app.post("/player/syndicate")
async def player_syndicate_endpoint(body: SyndicateRequest) -> JSONResponse:
    """
    Executes an underhanded shadow syndicate market manipulation operation.
    Supports Bandit Raids, Black Market Smuggling, and Price Fixing Cartels.
    """
    player_name = body.player_name or "You (Merchant)"
    if player_name not in sim_module.state.agents:
        sim_module.state.agents[player_name] = AgentState(
            name=player_name,
            persona="Player Merchant: Autonomous market participant seeking wealth and market control.",
            gold=100.0,
            inventory={"Health Potion": 2, "Iron Sword": 1, "Raw Gem": 2},
            is_player=True,
        )

    result = execute_syndicate_op(sim_module.state, body.op_type.value, body.item, player_name)

    anomalies = check_anomalies(sim_module.state)
    payload = _state_snapshot()
    payload["anomalies"] = anomalies
    payload["syndicate_result"] = result
    await manager.broadcast(payload)

    status_code = 200 if result.get("success", False) else 400
    return JSONResponse(
        content={
            **result,
            "state": _state_snapshot(),
        },
        status_code=status_code,
    )


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from src.config import settings
    uvicorn.run("src.main:app", host=settings.HOST, port=settings.PORT, reload=False)
