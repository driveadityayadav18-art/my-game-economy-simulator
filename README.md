# AI-Driven Game Economy Simulator

An asynchronous multi-agent economic simulation engine and real-time market simulator built with Python, FastAPI, and HTML5 WebSockets. Autonomous AI agents trade commodities based on mathematical supply/demand price discovery, while a Game Master cockpit and interactive merchant RPG layer allow real-time policy adjustments, shock events, crafting, and market intervention.

---

## Table of Contents

- [Overview](#overview)
- [Architecture & Mechanics](#architecture--mechanics)
- [Features](#features)
  - [1. Autonomous AI Persona Agents](#1-autonomous-ai-persona-agents)
  - [2. Macroeconomic & Policy Controls](#2-macroeconomic--policy-controls)
  - [3. Real-Time Visualization & Plaza Engine](#3-real-time-visualization--plaza-engine)
  - [4. Interactive Player Merchant & RPG Systems](#4-interactive-player-merchant--rpg-systems)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Usage Guide](#usage-guide)
  - [Running the Simulation](#running-the-simulation)
  - [Dashboard Controls & Policy Adjustments](#dashboard-controls--policy-adjustments)
  - [REST API Endpoints](#rest-api-endpoints)
  - [WebSocket API](#websocket-api)
- [Demo Previews & UI Walkthrough](#demo-previews--ui-walkthrough)
- [Testing & Verification](#testing--verification)
- [Known Limitations & Future Improvements](#known-limitations--future-improvements)
- [License](#license)

---

## Overview

The AI-Driven Game Economy Simulator models an in-game market economy driven by supply, demand, and agent behavior. 

Unlike static NPC shops with fixed prices, all commodity prices in this engine adjust dynamically using continuous clearing price formulas. Autonomous AI agents with distinct risk profiles and utility functions make trading decisions each tick. Operators and players can observe market fluctuations in real time, adjust systemic tax policies, trigger exogenous economic shocks, or participate directly as a merchant.

---

## Architecture & Mechanics

### Continuous Price Discovery Model

Commodity unit prices update every tick based on net aggregate market demand ($\Delta D = Q_{\text{bought}} - Q_{\text{sold}}$) and available supply:

$$\Delta D = \sum Q_{\text{buy}} - \sum Q_{\text{sell}}$$

$$P_{\text{new}} = \max\left(P_{\text{floor}}, \; P_{\text{old}} \cdot \left(1 + k \cdot \frac{\Delta D}{\text{Supply}_{\text{current}}}\right)\right)$$

- **$k$ (Price Sensitivity):** Configurable sensitivity constant (default: `0.05`).
- **$P_{\text{floor}}$:** Enforced minimum commodity price floor (default: `1.0 Gold`).
- **Supply Bounds:** Supply is conserved; purchasing reduces market stock, selling increases stock.

### Transaction Tax Mechanics

The royal treasury levies a percentage tax on each market trade:

$$\text{Tax} = P_{\text{unit}} \cdot Q \cdot r_{\text{tax}}$$

- **Buyer Total Outlay:** $(P \cdot Q) + \text{Tax}$
- **Seller Net Revenue:** $(P \cdot Q) - \text{Tax}$
- Tax rates can be adjusted dynamically between `0.0` (0%) and `0.80` (80%).

---

## Features

### 1. Autonomous AI Persona Agents
Three autonomous AI agents operate within the economy, each driven by distinct behavioral prompts and financial heuristics:
- **Garrick the Greedy:** Speculator persona. Accumulates gold and raw gems, buys during price depressions, and sells aggressively during market spikes.
- **Cora the Farmer:** Risk-averse producer. Consistently harvests and sells raw materials to maintain steady liquidity, avoiding debt and speculative buys.
- **Boran the Adventurer:** High-consumption warrior. Prioritizes gear and consumables (Potions and Swords), spends liquid gold quickly, and carries low cash reserves.

#### Multi-Provider LLM Support & Heuristic Fallback
- Supports **OpenAI** (`gpt-4o-mini`), **Anthropic** (`claude-3-5-haiku`), and **Google Gemini** (`gemini-1.5-flash`).
- All decisions adhere to a strict Pydantic JSON schema (`action`, `item`, `quantity`, `reasoning`).
- Runs **parallel execution** via `asyncio.gather()`.
- **Zero-Dependency Fallback:** If API keys are absent, network calls fail, or response latency exceeds 2.0 seconds, the engine automatically falls back to deterministic rule-based heuristics with zero simulation downtime.

---

### 2. Macroeconomic & Policy Controls
The Game Master cockpit exposes live macroeconomic levers:
- **Variable Tax Slider:** Adjust the royal transaction tax rate (`0%` – `80%`) in real time to observe liquidity compression and trade volume changes.
- **Simulation Speed Control:** Adjust tick rates dynamically between 0.5 seconds (fast demo) and 10.0 seconds (observational mode).
- **Economic Shock Triggers:**
  - 🐉 **Dragon Attack:** Potion supply drops to 2; potion clearing price spikes to 35.0 Gold.
  - 💰 **Gold Rush:** Injects +100 Gold directly into all agent balances.
  - 🌪️ **Trade War:** Surges tax rate to 50%, chilling market transactions.
  - 💣 **Market Crash:** Deflationary event dropping all commodity prices by 40%.
  - 🎰 **Black Market Surge:** Spikes commodity prices by 25% and injects +150 Gold into syndicate channels.

---

### 3. Real-Time Visualization & Plaza Engine
- **Bi-Directional WebSocket Stream:** Broadcasts complete economy snapshots (tick, prices, supply, agent balances, sentiment score, anomaly flags) after every tick.
- **Dynamic Price Chart:** Chart.js multi-series line chart tracking prices of Health Potions, Iron Swords, and Raw Gems across historical ticks.
- **2D Market Plaza Canvas:** 60 FPS HTML5 Canvas animation displaying agent sprites, merchant stalls, ambient particle systems (smoke, sparks, gold coins), and live action speech bubbles.
- **Anomaly Detection & Health Metrics:** Real-time Gini wealth inequality tracking, inflation indices, and market sentiment indicators.

---

### 4. Interactive Player Merchant & RPG Systems
- **Spot Trading Desk:** Buy and sell commodities directly against the market pool with live fee calculations and balance validation.
- **Expeditions & Quests:**
  - *Dungeon Raid:* Requires 1x Iron Sword + 1x Health Potion; rewards +50 Gold and consumables.
  - *Gem Prospecting:* Requires 1x Iron Sword; extracts +3 Raw Gems.
  - *Caravan Escort:* Requires 2x Health Potions + 1x Iron Sword; grants +120 Gold bounty.
- **Blacksmith & Alchemy Crafting:**
  - *Enchanted Blade:* Combines 1x Iron Sword + 1x Raw Gem + 5G fee.
  - *Greater Elixir:* Combines 1x Health Potion + 1x Raw Gem + 5G fee.
- **Shadow Syndicate Operations:**
  - *Bandit Raid:* Ambush supply routes to steal commodities and drive up scarcity.
  - *Contraband Smuggling:* Sell directly to the black market tax-free with interception risk.
  - *Cartel Price Fixing:* Collude with Garrick to artificially inflate clearing prices by +40%.

---

## Tech Stack

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Backend Runtime** | Python 3.10+ | Core async runtime |
| **Web Framework** | FastAPI | High-performance asynchronous REST & WebSocket framework |
| **ASGI Server** | Uvicorn | ASGI production web server |
| **Data Validation** | Pydantic v2 | Strict schema validation, serialization, and typing |
| **HTTP Client** | HTTPX | Asynchronous client for multi-provider LLM API calls |
| **Testing Suite** | Pytest + Pytest-Asyncio | Automated testing framework (316 unit, integration, and stress tests) |
| **Frontend UI** | HTML5 / ES6 JavaScript | Single-page client dashboard (served directly by FastAPI) |
| **Styling** | Tailwind CSS (CDN) | Responsive, high-contrast dashboard layout |
| **Charts** | Chart.js | Real-time commodity price visualization |
| **Graphics Engine** | HTML5 Canvas 2D | 60 FPS sprite and particle engine for the Market Plaza |
| **LLM Providers** | OpenAI / Anthropic / Gemini | Optional multi-provider LLM intelligence with heuristic fallback |

---

## Project Structure

```
my-game-economy-simulator/
├── src/
│   ├── __init__.py
│   ├── main.py          # FastAPI application, REST endpoints & WebSocket manager
│   ├── simulation.py    # Background tick loop and state management
│   ├── agents.py        # LLM persona prompts, API callers, and heuristic fallbacks
│   ├── market.py        # Pricing math, transaction validation, and shock events
│   ├── events.py        # Quests, crafting recipes, syndicate ops, and sentiment
│   ├── anomaly.py       # Anomaly detection, Gini inequality, and telemetry
│   ├── models.py        # Pydantic schemas, request/response models, and enums
│   ├── config.py        # Settings and environment configuration
│   └── index.html       # Web dashboard, 2D Plaza canvas, and Chart.js integration
├── tests/
│   ├── conftest.py
│   ├── test_market.py
│   ├── test_models.py
│   ├── test_config.py
│   ├── test_player_trade.py
│   ├── test_quests.py
│   ├── test_crafting.py
│   ├── test_syndicate.py
│   ├── test_tier1_features.py
│   ├── test_tier2_boundaries.py
│   ├── test_tier3_pairwise.py
│   ├── test_tier4_scenarios.py
│   └── test_tier5_adversarial.py
├── requirements.txt     # Python dependencies
├── ORIGINAL_REQUEST.md  # Specification reference
└── README.md
```

---

## Setup and Installation

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.14 installed
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/driveadityayadav18-art/my-game-economy-simulator.git
cd my-game-economy-simulator
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Optional Environment Configuration (`.env`)
The simulator runs fully out-of-the-box using deterministic heuristic models. If you wish to connect real LLM providers for agent decisions, create a `.env` file in the root directory:

```env
# Optional LLM Provider Configuration
LLM_PROVIDER=openai             # Options: openai | anthropic | gemini
OPENAI_API_KEY=your_openai_api_key_here
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
# GEMINI_API_KEY=your_gemini_api_key_here

# Simulation Knobs (Optional defaults)
SIMULATION_TICK_INTERVAL=4.0
DEFAULT_TAX_RATE=0.10
PRICE_SENSITIVITY_K=0.05
PRICE_FLOOR=1.0
```

---

## Usage Guide

### Running the Simulation

Start the FastAPI application with Uvicorn:

```bash
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:
```
http://localhost:8000
```

---

### Dashboard Controls & Policy Adjustments

1. **Simulation Execution:**
   - **Start Simulation (`▶ START`):** Starts the background loop (ticks occur automatically at the configured interval).
   - **Pause Simulation (`⏸ STOP`):** Freezes the simulation loop.
   - **Step Single Tick (`⏭ STEP TICK`):** Advances exactly one tick for deterministic analysis.
   - **Reset Simulation (`↺ RESET`):** Restores market supply, prices, and agent balances to genesis state.
   - **Speed Slider:** Slide between 0.5s and 10.0s per tick.

2. **Policy & Shock Testing:**
   - Adjust the **Tax Rate Slider** to modify the royal tax between 0% and 80%.
   - Click any shock button (**Dragon Attack**, **Gold Rush**, **Trade War**, **Market Crash**, **Black Market**) to trigger instant macroeconomic events.

3. **Player Operations:**
   - **Trading Desk:** Select an item, action (BUY/SELL), and quantity to execute spot transactions.
   - **Expeditions:** Launch Dungeon Raids, Gem Prospecting, or Caravan Escorts.
   - **Blacksmith:** Craft Enchanted Blades or Greater Elixirs.
   - **Syndicate:** Execute covert Bandit Raids, Contraband Smuggling, or Price-Fixing Cartels.

---

### REST API Endpoints

#### Simulation & State Endpoints
| Method | Endpoint | Description | Sample Response / Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Service healthcheck | `{"status": "ok", "service": "game-economy-simulator"}` |
| `GET` | `/state` | Full snapshot of current economy state | Full JSON state object |
| `POST` | `/simulation/start` | Starts continuous tick loop | `{"running": true, "tick": 12, "message": "Simulation loop started."}` |
| `POST` | `/simulation/stop` | Stops continuous tick loop | `{"running": false, "tick": 12, "message": "Simulation loop stopped."}` |
| `POST` | `/simulation/tick` | Executes a single simulation step | `{"message": "Tick #12 completed.", "transactions": [...]}` |
| `POST` | `/simulation/reset` | Resets economy to initial state | `{"running": false, "tick": 0, "message": "Economy reset to initial defaults."}` |

#### Macroeconomic Policy Endpoints
| Method | Endpoint | Description | Request Payload |
| :--- | :--- | :--- | :--- |
| `POST` | `/policy/tax` | Updates royal transaction tax rate | `{"tax_rate": 0.15}` |
| `POST` | `/policy/event` | Injects an economic shock event | `{"event": "Dragon Attack"}` |

#### Player Action Endpoints
| Method | Endpoint | Description | Request Payload |
| :--- | :--- | :--- | :--- |
| `POST` | `/player/trade` | Executes a manual spot market trade | `{"action": "BUY", "item": "Raw Gem", "quantity": 2}` |
| `POST` | `/player/quest` | Embarks on an adventure expedition | `{"quest_type": "DUNGEON_RAID"}` |
| `POST` | `/player/craft` | Crafts advanced manufactured goods | `{"recipe": "ENCHANTED_BLADE", "quantity": 1}` |
| `POST` | `/player/syndicate` | Executes covert syndicate operation | `{"op_type": "BANDIT_RAID", "item": "Raw Gem"}` |

---

### WebSocket API

- **Endpoint:** `ws://localhost:8000/ws`
- **Outgoing Stream (Server $\rightarrow$ Client):** Broadcasts state updates and anomaly alerts on every tick and player action:
  ```json
  {
    "tick": 14,
    "running": true,
    "tax_rate": 0.10,
    "items": {
      "Health Potion": {"name": "Health Potion", "price": 12.50, "supply": 18},
      "Iron Sword": {"name": "Iron Sword", "price": 25.00, "supply": 9},
      "Raw Gem": {"name": "Raw Gem", "price": 52.30, "supply": 14}
    },
    "agents": { ... },
    "recent_transactions": [ ... ],
    "sentiment": {"score": 68.5, "label": "Bullish"},
    "anomalies": []
  }
  ```
- **Incoming Controls (Client $\rightarrow$ Server):** Accepts real-time command payloads:
  ```json
  {"action": "set_tax", "tax_rate": 0.20}
  {"action": "trigger_event", "event": "Gold Rush"}
  {"action": "set_speed", "interval": 2.0}
  ```

---

## Demo Previews & UI Walkthrough

The web dashboard is split into distinct functional panels:

1. **Header & Status Bar:** Displays active tick count, loop status, average market liquidity, and current tax rate.
2. **Simulation Controls:** Dedicated buttons to play, pause, single-step, reset, and adjust tick intervals.
3. **Price Discovery Chart:** Live updating multi-line graph displaying commodity valuation trends over time.
4. **2D Animated Market Plaza:** Visual canvas depicting character interactions, stall positions, and floating event toasts.
5. **Macro Policy & Shock Deck:** Interactive buttons to trigger systemic economic shocks on demand.
6. **Player Trading Desk & Action Modules:** Interactive interfaces for trading, questing, crafting, and syndicate sabotage.
7. **Live Order Book & Transaction Feed:** Detailed real-time log of agent decisions, executed trades, and tax deductions.

---

## Testing & Verification

The project includes an automated test suite with **316 tests** validating pricing math, boundary conditions, race conditions, and adversarial scenarios.

### Running Tests

```bash
python -m pytest
```

### Test Coverage Highlights
- **Market Dynamics (`tests/test_market.py`):** Validates deterministic price discovery formulas, price floor enforcement, and supply conservation.
- **Player Actions (`tests/test_player_trade.py`, `test_quests.py`, `test_crafting.py`, `test_syndicate.py`):** Verifies inventory constraints, crafting recipes, quest loot tables, and syndicate risks.
- **Adversarial & Stress Tests (`tests/test_tier1_features.py` – `test_tier5_adversarial.py`):** Ensures float precision stability, handles malformed inputs, and validates fallback mechanisms under simulated latency.

---

## Known Limitations & Future Improvements

- **In-Memory Persistence:** Current simulation state is held in memory and resets when the server process terminates. Future versions will support persistent storage with SQLite or PostgreSQL.
- **Clearing Pool vs. Limit Order Book:** The current pricing model operates on a single aggregate clearing pool. Future work will implement a full dual-sided continuous double auction (CDA) order book.
- **Agent Population Scaling:** The default environment simulates 3 autonomous agents + 1 player. Future iterations can scale to hundreds of concurrent agents using background worker pools or spatial partitioning.
- **Multi-Region Trade Routes:** Expanding the economic model from a single central market to multiple regional cities with transport friction and regional supply advantages.

---

## License

This project is licensed under the [MIT License](LICENSE).
