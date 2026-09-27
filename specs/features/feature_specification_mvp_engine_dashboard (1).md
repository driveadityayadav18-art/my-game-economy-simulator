# Feature Spec: MVP Simulation Core & GM Dashboard

## 1. Feature Plan

### Component Architecture
1. **Simulation Engine (`main.py`):** Runs an infinite async tick loop every 4 seconds.
2. **Agent Module (`prompts.py`):** Formats state data, queries LLM with structured JSON output instructions, and parses decisions.
3. **Market Engine:** Processes buy/sell/craft orders, updates balances, and calculates new market prices.
4. **WebSocket Streamer:** Broadcasts complete state JSON to connected clients every tick.
5. **Dashboard UI (`index.html`):** Renders price charts, agent statuses, event logs, and sends policy update messages.

### Price Discovery Mechanics
Price adjustments are calculated based on net demand ($\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$) using the following formula:

$$P_{\text{new}} = \max\left(1.0, P_{\text{old}} \cdot \left(1 + k \cdot \Delta D\right)\right)$$

Where:
- $P_{\text{old}}$ = Current price of item
- $k$ = Sensitivity coefficient (default: $0.05$)
- $\Delta D$ = Net transaction quantity in current tick
- Minimum price bound = $1.0$ Gold

Tax deduction formula for transactions:

$$T = P_{\text{unit}} \cdot r_{\text{tax}}$$

---

## 2. Technical Requirements

### Agent Personas
1. **Garrick the Greedy:**
   - Goal: Hoard rare items and gold; buys low, sells high aggressively.
2. **Cora the Farmer:**
   - Goal: Steady income; sells raw materials consistently, avoids debt/risk.
3. **Boran the Adventurer:**
   - Goal: Immediate consumption; spends gold on potions/weapons, keeps low balance.

### Agent Decision JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "action": { "type": "string", "enum": ["BUY", "SELL", "CRAFT", "HOLD"] },
    "item": { "type": ["string", "null"], "enum": ["Health Potion", "Iron Sword", "Raw Gem", null] },
    "quantity": { "type": "integer", "minimum": 1, "maximum": 10 },
    "reasoning": { "type": "string", "maxLength": 120 }
  },
  "required": ["action", "item", "quantity", "reasoning"]
}
```

### GM Controls
- **Tax Rate Control:** Slider ranging from $0\%$ to $80\%$. Modifies $r_{\text{tax}}$ instantly.
- **Dragon Attack Event:** Sets Health Potion supply to $2$ and base price to $35.0$ Gold.
- **Gold Rush Event:** Immediately adds $+100$ Gold to all agent accounts.

---

## 3. Validation Scorecard

| Test ID | Scenario | Expected Outcome | Pass Criteria |
| :--- | :--- | :--- | :--- |
| **VAL-01** | Basic Tick Cycle | Loop executes every 4s, querying 3 agents in parallel. | Engine completes tick in $<2.0$ seconds. |
| **VAL-02** | Tax Impact | GM increases tax to $50\%$. | Agents log "HOLD" or complaints about high taxes in reasoning. |
| **VAL-03** | Dragon Attack Shock | Event triggered via UI. | Potion price spikes above $25.0$ Gold; News headline triggers alert. |
| **VAL-04** | Invalid LLM Response | LLM returns non-JSON text. | System falls back gracefully to "HOLD" without crashing loop. |
| **VAL-05** | Real-Time Sync | Web browser connects to `/ws`. | Chart updates continuously without needing page reload. |