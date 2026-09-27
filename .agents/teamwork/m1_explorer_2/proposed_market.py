"""
Market and Price Discovery Engine for AI-Driven Game Economy Simulator.

Implements pure mathematical pricing functions, transaction taxes,
gold and inventory constraints validation, atomic trade execution,
and macroeconomic shock mutators.
"""

from typing import Dict, List, Optional, Tuple
from src.models import (
    ActionType,
    AgentDecision,
    AgentState,
    EconomyState,
    ItemState,
    TransactionRecord,
)


def calculate_new_price(
    old_price: float,
    net_demand: int,
    k: float = 0.05,
    min_price: float = 1.0,
) -> float:
    """
    Computes updated item price based on net demand:
    P_new = max(min_price, round(old_price * (1 + k * net_demand), 2))

    Args:
        old_price: Current price of the item (must be >= min_price).
        net_demand: Net transaction quantity (Q_bought - Q_sold).
        k: Sensitivity coefficient (default: 0.05, 5% per unit of net demand).
        min_price: Absolute minimum price floor (default: 1.0 Gold).

    Returns:
        float: New item price rounded to 2 decimal places, clamped at min_price.
    """
    raw_price = old_price * (1.0 + k * float(net_demand))
    rounded_price = round(raw_price, 2)
    return max(min_price, rounded_price)


def calculate_tax(unit_price: float, quantity: int, tax_rate: float) -> float:
    """
    Computes transaction tax:
    T = round(unit_price * quantity * tax_rate, 2)

    Args:
        unit_price: Price per single item.
        quantity: Number of units traded.
        tax_rate: Current tax rate (clamped between 0.0 and 0.80).

    Returns:
        float: Tax amount rounded to 2 decimal places (>= 0.0).
    """
    if quantity <= 0 or unit_price <= 0.0 or tax_rate <= 0.0:
        return 0.0
    return round(unit_price * float(quantity) * float(tax_rate), 2)


def validate_transaction(
    agent: AgentState,
    item: Optional[ItemState],
    action: ActionType,
    quantity: int,
    tax_rate: float,
) -> Tuple[bool, str]:
    """
    Validates buyer gold or seller inventory constraints before trade execution.

    Args:
        agent: Agent attempting the trade.
        item: ItemState of the target commodity (can be None for HOLD/CRAFT).
        action: Transaction action (BUY, SELL, HOLD, CRAFT).
        quantity: Units to trade.
        tax_rate: Active market tax rate.

    Returns:
        Tuple[bool, str]: (is_valid, explanation_reason)
    """
    if action in (ActionType.HOLD, ActionType.CRAFT):
        return True, "Action requires no market transaction."

    if quantity <= 0:
        return False, f"Invalid quantity: {quantity}. Must be >= 1."

    if item is None:
        return False, f"Action '{action.value}' requires a valid item."

    if action == ActionType.BUY:
        # Check market supply
        if item.supply < quantity:
            return (
                False,
                f"Insufficient market supply: required {quantity}, available {item.supply}.",
            )

        # Check buyer gold: total_cost = unit_price * quantity + tax
        tax = calculate_tax(item.price, quantity, tax_rate)
        total_cost = round(item.price * float(quantity) + tax, 2)

        # Allow slight floating epsilon tolerance for precision
        if round(agent.gold, 2) + 1e-7 < total_cost:
            return (
                False,
                f"Insufficient gold: required {total_cost:.2f} Gold, available {agent.gold:.2f} Gold.",
            )

        return True, "BUY transaction valid."

    elif action == ActionType.SELL:
        # Check seller inventory
        current_inventory = agent.inventory.get(item.name, 0)
        if current_inventory < quantity:
            return (
                False,
                f"Insufficient inventory: agent has {current_inventory} of '{item.name}', required {quantity}.",
            )

        return True, "SELL transaction valid."

    return False, f"Unsupported action: {action}."


def execute_transaction(
    state: EconomyState, agent_name: str, decision: AgentDecision
) -> TransactionRecord:
    """
    Executes a transaction atomically against EconomyState.
    If valid: mutates agent gold/inventory, market supply, and records EXECUTED record.
    If invalid: preserves state without mutation and records REJECTED record.

    Args:
        state: In-memory EconomyState store.
        agent_name: Name of agent performing the trade.
        decision: Agent decision containing action, item, quantity, reasoning.

    Returns:
        TransactionRecord: Outcome record with status EXECUTED or REJECTED.
    """
    if agent_name not in state.agents:
        record = TransactionRecord(
            tick=state.tick,
            agent_name=agent_name,
            action=decision.action,
            item=decision.item,
            quantity=decision.quantity,
            unit_price=0.0,
            tax_paid=0.0,
            total_cost=0.0,
            status="REJECTED",
            reason=f"Agent '{agent_name}' does not exist in state.",
        )
        state.recent_transactions.append(record)
        return record

    agent = state.agents[agent_name]
    agent.last_action = decision

    # Handle HOLD or CRAFT
    if decision.action in (ActionType.HOLD, ActionType.CRAFT):
        record = TransactionRecord(
            tick=state.tick,
            agent_name=agent_name,
            action=decision.action,
            item=decision.item,
            quantity=decision.quantity,
            unit_price=0.0,
            tax_paid=0.0,
            total_cost=0.0,
            status="EXECUTED",
            reason=decision.reasoning or "HOLD action executed.",
        )
        state.recent_transactions.append(record)
        return record

    # Validate item existence
    if decision.item is None or decision.item not in state.items:
        record = TransactionRecord(
            tick=state.tick,
            agent_name=agent_name,
            action=decision.action,
            item=decision.item,
            quantity=decision.quantity,
            unit_price=0.0,
            tax_paid=0.0,
            total_cost=0.0,
            status="REJECTED",
            reason=f"Item '{decision.item}' not found in market catalog.",
        )
        state.recent_transactions.append(record)
        return record

    item_state = state.items[decision.item]
    is_valid, validation_msg = validate_transaction(
        agent=agent,
        item=item_state,
        action=decision.action,
        quantity=decision.quantity,
        tax_rate=state.tax_rate,
    )

    if not is_valid:
        record = TransactionRecord(
            tick=state.tick,
            agent_name=agent_name,
            action=decision.action,
            item=decision.item,
            quantity=decision.quantity,
            unit_price=item_state.price,
            tax_paid=0.0,
            total_cost=0.0,
            status="REJECTED",
            reason=validation_msg,
        )
        state.recent_transactions.append(record)
        return record

    # Atomic Execution for BUY
    if decision.action == ActionType.BUY:
        unit_price = item_state.price
        tax = calculate_tax(unit_price, decision.quantity, state.tax_rate)
        total_cost = round(unit_price * float(decision.quantity) + tax, 2)

        # Mutate agent
        agent.gold = round(agent.gold - total_cost, 2)
        agent.inventory[decision.item] = (
            agent.inventory.get(decision.item, 0) + decision.quantity
        )

        # Mutate market supply
        item_state.supply -= decision.quantity

        record = TransactionRecord(
            tick=state.tick,
            agent_name=agent_name,
            action=decision.action,
            item=decision.item,
            quantity=decision.quantity,
            unit_price=unit_price,
            tax_paid=tax,
            total_cost=total_cost,
            status="EXECUTED",
            reason=decision.reasoning or "BUY order executed successfully.",
        )
        state.recent_transactions.append(record)
        return record

    # Atomic Execution for SELL
    if decision.action == ActionType.SELL:
        unit_price = item_state.price
        revenue = round(unit_price * float(decision.quantity), 2)

        # Mutate agent
        agent.gold = round(agent.gold + revenue, 2)
        agent.inventory[decision.item] = (
            agent.inventory.get(decision.item, 0) - decision.quantity
        )

        # Mutate market supply
        item_state.supply += decision.quantity

        record = TransactionRecord(
            tick=state.tick,
            agent_name=agent_name,
            action=decision.action,
            item=decision.item,
            quantity=decision.quantity,
            unit_price=unit_price,
            tax_paid=0.0,
            total_cost=revenue,
            status="EXECUTED",
            reason=decision.reasoning or "SELL order executed successfully.",
        )
        state.recent_transactions.append(record)
        return record

    # Fallback rejection for unhandled action
    record = TransactionRecord(
        tick=state.tick,
        agent_name=agent_name,
        action=decision.action,
        item=decision.item,
        quantity=decision.quantity,
        unit_price=0.0,
        tax_paid=0.0,
        total_cost=0.0,
        status="REJECTED",
        reason=f"Unhandled action '{decision.action}'.",
    )
    state.recent_transactions.append(record)
    return record


def calculate_net_demand(
    transactions: List[TransactionRecord], item_name: str
) -> int:
    """
    Computes net demand ΔD = Q_bought - Q_sold for an item across EXECUTED transactions.

    Args:
        transactions: List of transaction records from current tick.
        item_name: Commodity identifier.

    Returns:
        int: Net demand ΔD.
    """
    bought = sum(
        t.quantity
        for t in transactions
        if t.item == item_name
        and t.action == ActionType.BUY
        and t.status == "EXECUTED"
    )
    sold = sum(
        t.quantity
        for t in transactions
        if t.item == item_name
        and t.action == ActionType.SELL
        and t.status == "EXECUTED"
    )
    return bought - sold


def update_market_prices(
    state: EconomyState,
    tick_transactions: List[TransactionRecord],
    k: float = 0.05,
    min_price: float = 1.0,
) -> Dict[str, float]:
    """
    Aggregates executed transactions in a tick and updates market prices.

    Args:
        state: EconomyState store.
        tick_transactions: All transaction records generated in the tick.
        k: Sensitivity parameter.
        min_price: Minimum price floor.

    Returns:
        Dict[str, float]: Mapping of item names to updated prices.
    """
    new_prices: Dict[str, float] = {}
    for item_name, item_state in state.items.items():
        delta_d = calculate_net_demand(tick_transactions, item_name)
        updated_price = calculate_new_price(
            old_price=item_state.price,
            net_demand=delta_d,
            k=k,
            min_price=min_price,
        )
        item_state.price = updated_price
        new_prices[item_name] = updated_price
    return new_prices


def apply_dragon_attack(state: EconomyState) -> None:
    """
    Applies the 'Dragon Attack' economic shock:
    Sets Health Potion supply = 2 and base price = 35.0 Gold.

    Args:
        state: In-memory EconomyState store to mutate.
    """
    potion_name = "Health Potion"
    if potion_name in state.items:
        state.items[potion_name].supply = 2
        state.items[potion_name].price = 35.0
    else:
        state.items[potion_name] = ItemState(
            name=potion_name, price=35.0, supply=2
        )


def apply_gold_rush(state: EconomyState, gold_amount: float = 100.0) -> None:
    """
    Applies the 'Gold Rush' economic shock:
    Credits gold_amount (default: 100.0) to all active agents.

    Args:
        state: In-memory EconomyState store to mutate.
        gold_amount: Amount of gold to credit each agent.
    """
    for agent in state.agents.values():
        agent.gold = round(agent.gold + gold_amount, 2)
