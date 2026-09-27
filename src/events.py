"""
Dynamic Lifecycle, Autonomous World Events, and Market Sentiment Engine.

Implements:
1. Agent Lifecycle Loops:
   - Cora: Harvests raw materials & earns farm income.
   - Boran: Consumes potions for Dungeon Raids, earning loot gold and rare finds.
   - Garrick: Speculative arbitrage, interest yield, and opportunistic hoarding.
2. Autonomous Stochastic World Events (Weather, Caravans, Monster Incursions, Mining Booms).
3. Market Sentiment (Fear & Greed Index).
4. Scenario Challenge Tracker for interactive GM goals.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional
from src.models import EconomyState, ActionType, TransactionRecord


# ---------------------------------------------------------------------------
# State tracking for lifecycle & world events
# ---------------------------------------------------------------------------
_last_world_event_tick = 0
_price_history_snapshots: List[Dict[str, float]] = []
_challenge_state: Dict[str, Any] = {
    "parity_streak": 0,
    "health_streak": 0,
    "completed_challenges": [],
}


def reset_event_engine():
    """Resets internal event engine counters."""
    global _last_world_event_tick, _price_history_snapshots, _challenge_state
    _last_world_event_tick = 0
    _price_history_snapshots.clear()
    _challenge_state = {
        "parity_streak": 0,
        "health_streak": 0,
        "completed_challenges": [],
    }


# ---------------------------------------------------------------------------
# 1. Agent Lifecycle Loops
# ---------------------------------------------------------------------------

def process_agent_lifecycles(state: EconomyState) -> List[str]:
    """
    Executes autonomous lifecycle actions each tick for active agents:
    - Cora: Regenerates raw materials from harvest and earns minor farm income.
    - Boran: Embarks on dungeon raids, consuming Health Potions for high loot gold.
    - Garrick: Collects treasury yield and looks for cornering opportunities.

    Returns a list of human-readable telemetry activity logs.
    """
    logs: List[str] = []

    # --- Cora the Farmer: Harvest & Farmstand Cycle ---
    cora = state.agents.get("Cora the Farmer")
    if cora:
        # Every 2 ticks, Cora harvests raw gems / herbs
        if state.tick % 2 == 0:
            harvest_yield = random.randint(1, 3)
            current_gems = cora.inventory.get("Raw Gem", 0)
            if current_gems + harvest_yield <= 30:
                cora.inventory["Raw Gem"] = current_gems + harvest_yield
                farm_income = round(random.uniform(4.0, 9.0), 2)
                cora.gold = round(cora.gold + farm_income, 2)
                logs.append(f"🌾 Cora harvested +{harvest_yield} Raw Gems & earned {farm_income}G from local farmstand.")

    # --- Boran the Adventurer: Dungeon Raid & Loot Cycle ---
    boran = state.agents.get("Boran the Adventurer")
    if boran:
        # Every 3 ticks, Boran embarks on a dungeon expedition
        if state.tick % 3 == 0 and state.tick > 0:
            potions = boran.inventory.get("Health Potion", 0)
            swords = boran.inventory.get("Iron Sword", 0)

            if potions >= 1:
                # Consume 1 potion for a deep dungeon raid
                boran.inventory["Health Potion"] = potions - 1
                loot_gold = round(random.uniform(35.0, 75.0), 2)
                boran.gold = round(boran.gold + loot_gold, 2)

                # 35% chance to find ancient raw gems in dungeon
                found_gem = random.random() < 0.35
                if found_gem:
                    boran.inventory["Raw Gem"] = boran.inventory.get("Raw Gem", 0) + 1
                    logs.append(f"⚔️ Boran raided Dungeon Vault: consumed 1 Potion, looted +{loot_gold}G and 1 Ancient Gem!")
                else:
                    logs.append(f"⚔️ Boran raided Dungeon Floor: consumed 1 Potion, looted +{loot_gold}G from dungeon boss!")
            else:
                # No potions: high risk skirmish with low reward
                scout_gold = round(random.uniform(8.0, 18.0), 2)
                boran.gold = round(boran.gold + scout_gold, 2)
                logs.append(f"⚔️ Boran completed a low-tier scout patrol (No Potions): earned +{scout_gold}G.")

    # --- Garrick the Greedy: Treasury Interest & Speculation ---
    garrick = state.agents.get("Garrick the Greedy")
    if garrick:
        # Every 4 ticks, Garrick collects 2% interest on treasury reserves above 100G
        if state.tick % 4 == 0 and garrick.gold > 100.0:
            interest = round(garrick.gold * 0.02, 2)
            garrick.gold = round(garrick.gold + interest, 2)
            logs.append(f"💰 Garrick banked +{interest}G capital dividends on reserve liquidity.")

    return logs


# ---------------------------------------------------------------------------
# 2. Autonomous Stochastic World Events Engine
# ---------------------------------------------------------------------------

WORLD_EVENTS = [
    {
        "name": "Bumper Crop Harvest",
        "icon": "🌾",
        "type": "HARVEST",
        "description": "Favorable climate yields double gem harvest! Gem market supply floods.",
        "effect": "gems_boost",
    },
    {
        "name": "Monster Horde Incursion",
        "icon": "👾",
        "type": "MONSTERS",
        "description": "Wild monster horde threatens the frontier! Demand for Swords & Potions surges.",
        "effect": "gear_surge",
    },
    {
        "name": "Wandering Merchant Caravan",
        "icon": "🐫",
        "type": "CARAVAN",
        "description": "Silk Road traders arrive and purchase surplus stock from the public exchange.",
        "effect": "caravan_buy",
    },
    {
        "name": "Gold Vein Discovered",
        "icon": "⛏️",
        "type": "MINING",
        "description": "Prospectors strike gold! All agents receive +30G windfall.",
        "effect": "gold_rush_small",
    },
    {
        "name": "Alchemical Drought",
        "icon": "☀️",
        "type": "DROUGHT",
        "description": "Herb scarcity limits potion brewing. Potion prices spike +25%.",
        "effect": "potion_spike",
    },
]


def process_autonomous_events(state: EconomyState) -> Optional[Dict[str, Any]]:
    """
    Evaluates whether an autonomous world event occurs this tick.
    Triggers roughly every 7 to 12 ticks dynamically.
    """
    global _last_world_event_tick

    if state.tick < 4:
        return None

    ticks_since_last = state.tick - _last_world_event_tick
    # Event probability increases as ticks elapse
    if ticks_since_last >= 8 and random.random() < 0.40:
        event = random.choice(WORLD_EVENTS)
        _last_world_event_tick = state.tick

        # Apply event effect
        effect = event["effect"]
        if effect == "gems_boost":
            if "Raw Gem" in state.items:
                state.items["Raw Gem"].supply += 15
                state.items["Raw Gem"].price = max(1.0, round(state.items["Raw Gem"].price * 0.85, 2))
            cora = state.agents.get("Cora the Farmer")
            if cora:
                cora.inventory["Raw Gem"] = cora.inventory.get("Raw Gem", 0) + 5

        elif effect == "gear_surge":
            for item_name in ("Health Potion", "Iron Sword"):
                if item_name in state.items:
                    state.items[item_name].price = round(state.items[item_name].price * 1.25, 2)
            boran = state.agents.get("Boran the Adventurer")
            if boran:
                boran.gold = round(boran.gold + 40.0, 2)

        elif effect == "caravan_buy":
            # Caravan injects demand and gold
            for item in state.items.values():
                item.supply = max(2, item.supply - 3)
                item.price = round(item.price * 1.10, 2)
            for agent in state.agents.values():
                agent.gold = round(agent.gold + 20.0, 2)

        elif effect == "gold_rush_small":
            for agent in state.agents.values():
                agent.gold = round(agent.gold + 30.0, 2)

        elif effect == "potion_spike":
            if "Health Potion" in state.items:
                state.items["Health Potion"].price = round(state.items["Health Potion"].price * 1.30, 2)
                state.items["Health Potion"].supply = max(1, state.items["Health Potion"].supply - 5)

        return {
            "type": "WORLD_EVENT",
            "name": event["name"],
            "icon": event["icon"],
            "headline": f"{event['icon']} {event['name'].upper()}: {event['description']}",
            "tick": state.tick,
        }

    return None


# ---------------------------------------------------------------------------
# 3. Market Sentiment (Fear & Greed Index)
# ---------------------------------------------------------------------------

def calculate_market_sentiment(state: EconomyState) -> Dict[str, Any]:
    """
    Computes real-time Market Fear & Greed Index [0 to 100].
    Takes into account price velocity, trading activity, and wealth inequality.
    """
    global _price_history_snapshots

    current_prices = {k: v.price for k, v in state.items.items()}
    _price_history_snapshots.append(current_prices)
    if len(_price_history_snapshots) > 10:
        _price_history_snapshots.pop(0)

    score = 50.0  # Baseline neutral

    # Factor 1: Price momentum over recent ticks
    if len(_price_history_snapshots) >= 2:
        prev = _price_history_snapshots[-2]
        curr = _price_history_snapshots[-1]
        for name in curr:
            if name in prev and prev[name] > 0:
                diff_pct = (curr[name] - prev[name]) / prev[name]
                score += diff_pct * 40.0

    # Factor 2: Trade activity volume
    recent_exec = [t for t in state.recent_transactions[-6:] if t.status == "EXECUTED" and t.action != ActionType.HOLD]
    score += len(recent_exec) * 3.5

    # Factor 3: Tax penalty (high taxes generate fear)
    if state.tax_rate >= 0.40:
        score -= (state.tax_rate - 0.30) * 50.0

    score = max(5, min(95, round(score)))

    if score < 25:
        category = "EXTREME FEAR"
        color = "#f43f5e"
        icon = "😱"
    elif score < 45:
        category = "FEAR"
        color = "#facc15"
        icon = "😨"
    elif score <= 60:
        category = "NEUTRAL"
        color = "#06b6d4"
        icon = "⚖️"
    elif score <= 80:
        category = "GREED"
        color = "#a3e635"
        icon = "🤑"
    else:
        category = "EUPHORIA"
        color = "#bef264"
        icon = "🚀"

    return {
        "score": score,
        "category": category,
        "color": color,
        "icon": icon,
    }


# ---------------------------------------------------------------------------
# 4. Scenario Challenges / GM Missions Tracker
# ---------------------------------------------------------------------------

def evaluate_challenges(state: EconomyState) -> List[Dict[str, Any]]:
    """
    Tracks active Game Master challenge objectives and returns live progress.
    """
    global _challenge_state

    # 1. Wealth Parity Challenge: keep max/min gold ratio < 4.0
    golds = [a.gold for a in state.agents.values() if a.gold > 0]
    disparity = (max(golds) / max(min(golds), 1.0)) if len(golds) >= 2 else 1.0
    if disparity <= 4.0:
        _challenge_state["parity_streak"] += 1
    else:
        _challenge_state["parity_streak"] = max(0, _challenge_state["parity_streak"] - 1)

    parity_goal = 12
    parity_done = _challenge_state["parity_streak"] >= parity_goal

    # 2. Market Velocity Challenge: 15 total executed trades
    total_trades = sum(1 for t in state.recent_transactions if t.status == "EXECUTED" and t.action != ActionType.HOLD)
    trades_goal = 12
    trades_done = total_trades >= trades_goal

    # 3. Solvency Challenge: Keep Boran gold > 20G for 10 ticks
    boran = state.agents.get("Boran the Adventurer")
    boran_solvent = (boran.gold >= 25.0) if boran else False

    return [
        {
            "id": "parity",
            "title": "WEALTH EQUITY",
            "desc": "Keep wealth disparity < 4.0x",
            "current": f"{disparity:.1f}x (Streak {_challenge_state['parity_streak']}/{parity_goal})",
            "completed": parity_done,
        },
        {
            "id": "velocity",
            "title": "MARKET VELOCITY",
            "desc": "Achieve 12 executed trades",
            "current": f"{total_trades}/{trades_goal} Trades",
            "completed": trades_done,
        },
        {
            "id": "adventurer",
            "title": "DUNGEON SOLVENCY",
            "desc": "Keep Boran liquid (>25G)",
            "current": f"{boran.gold:.1f}G" if boran else "N/A",
            "completed": boran_solvent,
        },
    ]


# ---------------------------------------------------------------------------
# 5. Quest and Expedition Resolver
# ---------------------------------------------------------------------------

def execute_quest(state: EconomyState, quest_type: str, agent_name: str = "You (Merchant)") -> Dict[str, Any]:
    """
    Executes a high-stakes adventure, prospecting, or caravan contract.
    Validates gear prerequisites, consumes consumables, calculates rewards or penalties.
    """
    if agent_name not in state.agents:
        return {
            "success": False,
            "status": "REJECTED",
            "message": f"Agent '{agent_name}' not found.",
        }

    agent = state.agents[agent_name]
    potions = agent.inventory.get("Health Potion", 0)
    swords = agent.inventory.get("Iron Sword", 0)
    gems = agent.inventory.get("Raw Gem", 0)

    q_type = quest_type.upper().replace(" ", "_")

    if q_type == "DUNGEON_RAID":
        if potions >= 1 and swords >= 1:
            # Consumes 1 potion for boss encounter
            agent.inventory["Health Potion"] = potions - 1
            loot_gold = round(random.uniform(45.0, 90.0), 2)
            agent.gold = round(agent.gold + loot_gold, 2)
            found_gem = random.random() < 0.40
            gem_text = ""
            if found_gem:
                agent.inventory["Raw Gem"] = gems + 1
                gem_text = " and unearthed 1x Ancient Raw Gem"

            reason = f"Dungeon Vault conquered: looted +{loot_gold}G{gem_text}!"
            state.recent_transactions.append(
                TransactionRecord(
                    tick=state.tick,
                    agent_name=agent_name,
                    action=ActionType.CRAFT,
                    item="Health Potion",
                    quantity=1,
                    unit_price=0.0,
                    tax_paid=0.0,
                    total_cost=loot_gold,
                    status="EXECUTED",
                    reason=reason,
                )
            )
            return {
                "success": True,
                "status": "SUCCESS",
                "loot_gold": loot_gold,
                "gems_found": 1 if found_gem else 0,
                "message": f"🏆 {reason}",
                "agent": agent.model_dump(),
            }
        else:
            # Underprepared raid: 50% injury penalty, 50% minor scout
            if random.random() < 0.50:
                injury_penalty = min(agent.gold, 20.0)
                agent.gold = round(agent.gold - injury_penalty, 2)
                reason = f"Dungeon Ambush (No Potions/Sword): Wounded! Paid {injury_penalty}G in surgeon fees."
                return {
                    "success": False,
                    "status": "INJURED",
                    "loot_gold": -injury_penalty,
                    "gems_found": 0,
                    "message": f"🩸 {reason}",
                    "agent": agent.model_dump(),
                }
            else:
                scout_gold = round(random.uniform(10.0, 20.0), 2)
                agent.gold = round(agent.gold + scout_gold, 2)
                reason = f"Cautious Perimeter Scout: Barely survived, gathered +{scout_gold}G."
                return {
                    "success": True,
                    "status": "SCOUT_SUCCESS",
                    "loot_gold": scout_gold,
                    "gems_found": 0,
                    "message": f"⚠️ {reason}",
                    "agent": agent.model_dump(),
                }

    elif q_type == "GEM_PROSPECTING":
        if swords >= 1:
            mined_gems = random.randint(2, 5)
            agent.inventory["Raw Gem"] = gems + mined_gems
            bonus_gold = round(random.uniform(15.0, 30.0), 2)
            agent.gold = round(agent.gold + bonus_gold, 2)

            reason = f"Deep Vein Prospecting: Mined +{mined_gems}x Raw Gems and +{bonus_gold}G gold nuggets."
            state.recent_transactions.append(
                TransactionRecord(
                    tick=state.tick,
                    agent_name=agent_name,
                    action=ActionType.CRAFT,
                    item="Raw Gem",
                    quantity=mined_gems,
                    unit_price=0.0,
                    tax_paid=0.0,
                    total_cost=bonus_gold,
                    status="EXECUTED",
                    reason=reason,
                )
            )
            return {
                "success": True,
                "status": "SUCCESS",
                "loot_gold": bonus_gold,
                "gems_found": mined_gems,
                "message": f"⛏️ {reason}",
                "agent": agent.model_dump(),
            }
        else:
            return {
                "success": False,
                "status": "MISSING_GEAR",
                "message": "⚠️ Gem Prospecting requires at least 1x Iron Sword (mining tool) in your vault.",
            }

    elif q_type == "CARAVAN_ESCORT":
        if potions >= 2 and swords >= 1:
            agent.inventory["Health Potion"] = potions - 1
            escort_bounty = round(random.uniform(75.0, 130.0), 2)
            agent.gold = round(agent.gold + escort_bounty, 2)
            agent.inventory["Raw Gem"] = gems + 1

            reason = f"Caravan Escort Completed: Repelled bandits, earned +{escort_bounty}G bounty and +1x Raw Gem bonus."
            state.recent_transactions.append(
                TransactionRecord(
                    tick=state.tick,
                    agent_name=agent_name,
                    action=ActionType.CRAFT,
                    item="Iron Sword",
                    quantity=1,
                    unit_price=0.0,
                    tax_paid=0.0,
                    total_cost=escort_bounty,
                    status="EXECUTED",
                    reason=reason,
                )
            )
            return {
                "success": True,
                "status": "SUCCESS",
                "loot_gold": escort_bounty,
                "gems_found": 1,
                "message": f"🐫 {reason}",
                "agent": agent.model_dump(),
            }
        else:
            return {
                "success": False,
                "status": "MISSING_GEAR",
                "message": f"⚠️ Caravan Escort requires 2x Health Potions and 1x Iron Sword. You have {potions} Potions, {swords} Swords.",
            }

    return {
        "success": False,
        "status": "UNKNOWN_QUEST",
        "message": f"Unknown quest type '{quest_type}'. Valid: DUNGEON_RAID, GEM_PROSPECTING, CARAVAN_ESCORT.",
    }


# ---------------------------------------------------------------------------
# 6. Crafting & Alchemy Resolver
# ---------------------------------------------------------------------------

def execute_craft(
    state: EconomyState, recipe: str, quantity: int = 1, agent_name: str = "You (Merchant)"
) -> Dict[str, Any]:
    """
    Executes an alchemy or blacksmith crafting recipe.
    Deducts raw materials & forging fee, and adds advanced item to inventory.
    """
    if agent_name not in state.agents:
        return {
            "success": False,
            "status": "REJECTED",
            "message": f"Agent '{agent_name}' not found.",
        }

    agent = state.agents[agent_name]
    qty = max(1, min(10, quantity))
    rec = recipe.upper().replace(" ", "_")

    if rec == "ENCHANTED_BLADE":
        swords = agent.inventory.get("Iron Sword", 0)
        gems = agent.inventory.get("Raw Gem", 0)
        fee = round(5.0 * qty, 2)

        if swords < qty or gems < qty or agent.gold < fee:
            return {
                "success": False,
                "status": "MISSING_MATERIALS",
                "message": f"⚠️ Need {qty}x Iron Sword, {qty}x Raw Gem, and {fee}G forge fee. (Have: {swords} Swd, {gems} Gem, {agent.gold}G)",
            }

        agent.inventory["Iron Sword"] = swords - qty
        agent.inventory["Raw Gem"] = gems - qty
        agent.gold = round(agent.gold - fee, 2)
        agent.inventory["Enchanted Blade"] = agent.inventory.get("Enchanted Blade", 0) + qty

        reason = f"Forged {qty}x ✨ Enchanted Blade from Iron Swords & Raw Gems (-{fee}G fee)."
        state.recent_transactions.append(
            TransactionRecord(
                tick=state.tick,
                agent_name=agent_name,
                action=ActionType.CRAFT,
                item="Iron Sword",
                quantity=qty,
                unit_price=0.0,
                tax_paid=0.0,
                total_cost=fee,
                status="EXECUTED",
                reason=reason,
            )
        )
        return {
            "success": True,
            "status": "SUCCESS",
            "item_crafted": "Enchanted Blade",
            "quantity": qty,
            "fee_paid": fee,
            "message": f"⚒️ {reason}",
            "agent": agent.model_dump(),
        }

    elif rec == "GREATER_ELIXIR":
        potions = agent.inventory.get("Health Potion", 0)
        gems = agent.inventory.get("Raw Gem", 0)
        fee = round(5.0 * qty, 2)

        if potions < qty or gems < qty or agent.gold < fee:
            return {
                "success": False,
                "status": "MISSING_MATERIALS",
                "message": f"⚠️ Need {qty}x Health Potion, {qty}x Raw Gem, and {fee}G alchemy fee. (Have: {potions} HP, {gems} Gem, {agent.gold}G)",
            }

        agent.inventory["Health Potion"] = potions - qty
        agent.inventory["Raw Gem"] = gems - qty
        agent.gold = round(agent.gold - fee, 2)
        agent.inventory["Greater Elixir"] = agent.inventory.get("Greater Elixir", 0) + qty

        reason = f"Brewed {qty}x 🧪 Greater Elixir in Alchemy Lab (-{fee}G fee)."
        state.recent_transactions.append(
            TransactionRecord(
                tick=state.tick,
                agent_name=agent_name,
                action=ActionType.CRAFT,
                item="Health Potion",
                quantity=qty,
                unit_price=0.0,
                tax_paid=0.0,
                total_cost=fee,
                status="EXECUTED",
                reason=reason,
            )
        )
        return {
            "success": True,
            "status": "SUCCESS",
            "item_crafted": "Greater Elixir",
            "quantity": qty,
            "fee_paid": fee,
            "message": f"🧪 {reason}",
            "agent": agent.model_dump(),
        }

    return {
        "success": False,
        "status": "UNKNOWN_RECIPE",
        "message": f"Unknown recipe '{recipe}'. Valid: ENCHANTED_BLADE, GREATER_ELIXIR.",
    }


# ---------------------------------------------------------------------------
# 7. Shadow Syndicate & Crime Resolver
# ---------------------------------------------------------------------------

def execute_syndicate_op(
    state: EconomyState, op_type: str, item_name: Optional[str] = None, agent_name: str = "You (Merchant)"
) -> Dict[str, Any]:
    """
    Executes a shadow syndicate market manipulation operation:
    - BANDIT_RAID: Pays 30G to raid Cora's gem shipments, reducing supply and spiking prices +35%.
    - SMUGGLE_RUN: Sells 1x commodity bypassing government tax. 25% risk of royal customs bust (-35G).
    - CARTEL_PRICE_FIX: Pays Garrick 40G kickback to fix potion/sword price floor (+40% price surge).
    """
    if agent_name not in state.agents:
        return {
            "success": False,
            "status": "REJECTED",
            "message": f"Agent '{agent_name}' not found.",
        }

    agent = state.agents[agent_name]
    op = op_type.upper().replace(" ", "_")

    if op == "BANDIT_RAID":
        cost = 30.0
        if agent.gold < cost:
            return {
                "success": False,
                "status": "INSUFFICIENT_FUNDS",
                "message": f"⚠️ Bandit Raid requires {cost}G mercenary hire fee. (You have {agent.gold}G)",
            }

        agent.gold = round(agent.gold - cost, 2)
        cora = state.agents.get("Cora the Farmer")
        stolen_gems = 0
        if cora:
            stolen_gems = max(1, cora.inventory.get("Raw Gem", 0) // 2)
            cora.inventory["Raw Gem"] = max(0, cora.inventory.get("Raw Gem", 0) - stolen_gems)

        if "Raw Gem" in state.items:
            state.items["Raw Gem"].supply = max(5, int(state.items["Raw Gem"].supply * 0.65))
            state.items["Raw Gem"].price = round(state.items["Raw Gem"].price * 1.35, 2)

        reason = f"🏴‍☠️ Bandit Sabotage: Raided Cora's gem reserves (-{stolen_gems} gems) & spiked market price to {state.items['Raw Gem'].price}G!"
        state.recent_transactions.append(
            TransactionRecord(
                tick=state.tick,
                agent_name=agent_name,
                action=ActionType.CRAFT,
                item="Raw Gem",
                quantity=stolen_gems,
                unit_price=0.0,
                tax_paid=0.0,
                total_cost=cost,
                status="EXECUTED",
                reason=reason,
            )
        )
        return {
            "success": True,
            "status": "SUCCESS",
            "operation": "BANDIT_RAID",
            "cost_paid": cost,
            "stolen_gems": stolen_gems,
            "new_price": state.items["Raw Gem"].price if "Raw Gem" in state.items else 0,
            "message": reason,
            "agent": agent.model_dump(),
        }

    elif op == "SMUGGLE_RUN":
        target = item_name or "Raw Gem"
        if target not in state.items:
            target = "Raw Gem"

        item_stock = agent.inventory.get(target, 0)
        if item_stock < 1:
            return {
                "success": False,
                "status": "MISSING_CONTRABAND",
                "message": f"⚠️ Smuggle run requires at least 1x {target} in your vault to smuggle.",
            }

        # 25% chance of customs bust
        is_busted = random.random() < 0.25
        if is_busted:
            fine = min(agent.gold, 35.0)
            agent.gold = round(agent.gold - fine, 2)
            reason = f"🚨 Customs Interception! Royal guards confiscated 1x {target} and fined you {fine}G!"
            agent.inventory[target] = item_stock - 1
            return {
                "success": False,
                "status": "BUSTED",
                "fine_paid": fine,
                "message": reason,
                "agent": agent.model_dump(),
            }
        else:
            # Clean evade: full spot price with 0% tax!
            unit_price = state.items[target].price
            agent.inventory[target] = item_stock - 1
            agent.gold = round(agent.gold + unit_price, 2)
            state.items[target].supply += 1
            reason = f"🕵️ Black Market Smuggle: Evaded 100% tax and fenced 1x {target} for clean +{unit_price:.1f}G!"
            state.recent_transactions.append(
                TransactionRecord(
                    tick=state.tick,
                    agent_name=agent_name,
                    action=ActionType.SELL,
                    item=target,
                    quantity=1,
                    unit_price=unit_price,
                    tax_paid=0.0,
                    total_cost=unit_price,
                    status="EXECUTED",
                    reason=reason,
                )
            )
            return {
                "success": True,
                "status": "SUCCESS",
                "payout": unit_price,
                "tax_evaded": round(unit_price * state.tax_rate, 2),
                "message": reason,
                "agent": agent.model_dump(),
            }

    elif op == "CARTEL_PRICE_FIX":
        cost = 40.0
        if agent.gold < cost:
            return {
                "success": False,
                "status": "INSUFFICIENT_FUNDS",
                "message": f"⚠️ Cartel price fixing requires {cost}G syndicate bribery pool. (You have {agent.gold}G)",
            }

        agent.gold = round(agent.gold - cost, 2)
        garrick = state.agents.get("Garrick the Greedy")
        if garrick:
            garrick.gold = round(garrick.gold + cost, 2)

        # Spike Health Potion and Sword prices
        if "Health Potion" in state.items:
            state.items["Health Potion"].price = round(state.items["Health Potion"].price * 1.40, 2)
        if "Iron Sword" in state.items:
            state.items["Iron Sword"].price = round(state.items["Iron Sword"].price * 1.30, 2)

        reason = f"🤝 Monopoly Cartel Sealed: Paid Garrick 40G bribe. Potion & Sword prices jacked up +40%!"
        state.recent_transactions.append(
            TransactionRecord(
                tick=state.tick,
                agent_name=agent_name,
                action=ActionType.CRAFT,
                item="Health Potion",
                quantity=1,
                unit_price=0.0,
                tax_paid=0.0,
                total_cost=cost,
                status="EXECUTED",
                reason=reason,
            )
        )
        return {
            "success": True,
            "status": "SUCCESS",
            "operation": "CARTEL_PRICE_FIX",
            "bribe_paid": cost,
            "message": reason,
            "agent": agent.model_dump(),
        }

    return {
        "success": False,
        "status": "UNKNOWN_OP",
        "message": f"Unknown syndicate operation '{op_type}'. Valid: BANDIT_RAID, SMUGGLE_RUN, CARTEL_PRICE_FIX.",
    }



