# ⚔️ AI-DRIVEN GAME ECONOMY SIMULATOR
### *An Autonomous Multi-Agent Fantasy Economy, Real-Time Market Discovery Engine & Interactive Merchant RPG*

[![Tests](https://img.shields.io/badge/Tests-316%20Passed%20(100%25)-brightgreen.svg?style=for-the-badge&logo=pytest)](https://pytest.org)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![WebSocket](https://img.shields.io/badge/WebSocket-Real--Time%20Stream-FF6F00.svg?style=for-the-badge&logo=websocket)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![UI](https://img.shields.io/badge/Design-Acid%20Punk%20Neo--Brutalist-FAFF00.svg?style=for-the-badge)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/License-MIT-purple.svg?style=for-the-badge)](LICENSE)

---

## 📖 Executive Summary & Hackathon Vision

Modern MMORPGs and simulated sandbox games suffer from **static shopkeeper economies** and **rampant hyperinflation**. 

**AI-Driven Game Economy Simulator** revolutionizes virtual game worlds by introducing an **autonomous, agentic living economy**. Three AI agents with unique personas and behavioral decision models trade commodities dynamically against continuous order books. Human players can step into the shoes of a merchant trader—buying and selling goods, embarking on high-risk dungeon expeditions, forging enchanted weapons in the Blacksmith Lab, and launching covert Shadow Syndicate operations to sabotage rivals.

The entire simulation runs with **zero mandatory API dependencies**, features a **60 FPS Neo-Brutalist 2D Animated Market Plaza**, and provides a **God-Mode Game Master Cockpit** to inject macroeconomic shocks, adjust tax policy, and monitor Gini wealth disparities in real time.

---

## ⚡ Quickstart Guide (Get Running in 60 Seconds)

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/my-game-economy-simulator.git
cd my-game-economy-simulator
pip install -r requirements.txt
```

### 2. Launch the Application
```bash
python -m uvicorn src.main:app --reload --port 8000
```

### 3. Open the Cockpit
Navigate to [http://localhost:8000](http://localhost:8000) in your web browser. 
*(No configuration or API keys required out of the box!)*

---

## 🎮 Core Gameplay Systems & Features

### 1. 🧙‍♂️ Playable Player Merchant Mode & Spot Trading Desk
* **Live Liquidity Floor**: Buy and sell **Health Potions**, **Iron Swords**, and **Raw Gems** directly into the market clearing pool.
* **Instant Dynamic Pricing**: Player transactions immediately impact continuous price discovery, adjust commodity supplies, and deduct royal transaction taxes.
* **Smart UI Calculators**: Live order preview calculating exact gross costs, dynamic tax deductions, net revenues, and max-buy limits.

### 2. 🛡️ Expeditions, Quests & Consequences Engine
Turn commodities into survival tools with real economic payouts:
* 🗡️ **Dungeon Raid**: Requires `1x Iron Sword` + `1x Health Potion`. High risk, high reward. Grants `+50G` loot and consumable restocking. Failing without gear inflicts player injury fines.
* 💎 **Gem Prospecting**: Requires `1x Iron Sword` as an excavation pick. Mines `+3 Raw Gems` into vault reserves.
* 🛡️ **Caravan Escort**: High-stakes merchant protection requiring `2x Health Potions` + `1x Iron Sword`. Generates massive `+120G` royal bounty payouts!

### 3. 🔨 Blacksmith Forge & Alchemy Lab (Crafting Supply Chain)
Arbitrage raw materials and transform low-margin commodities into high-value luxury goods:
* ⚔️ **Enchanted Blade**: Forged with `1x Iron Sword` + `1x Raw Gem` + `5G Fee`. Resells at massive margins.
* 🧪 **Greater Elixir**: Brewed with `1x Health Potion` + `1x Raw Gem` + `5G Fee`. Essential high-tier consumable.

### 4. 🥷 Shadow Syndicate Ops (Crime, Cartels & Sabotage)
Underhanded economic warfare for ruthless merchants:
* 🦹 **Bandit Sabotage Raid** *(25G)*: Hire cutthroats to ambush Cora's supply convoy, stealing 3 Raw Gems from her vault and driving up scarcity prices.
* 📦 **Contraband Smuggling** *(15G)*: Offload 3 Raw Gems off the books directly to the black market, evading royal taxes with a 20% risk of customs interception fines.
* 🤝 **Garrick Cartel Price-Fixing** *(30G)*: Bribe Garrick the Greedy with 30G to lock arms and inflate Raw Gem clearing prices by `+40%` for instant market manipulation!

### 5. 🎪 2D Animated Market Plaza Canvas Engine
* **60 FPS Neo-Brutalist Visual Canvas (`800x240`)**:
  * 🌿 **Cora's Botanical Garden**: Herb greenhouses, bubbling cauldron smoke particles, and potion displays.
  * 👑 **Garrick's Gold Vault**: Reinforced iron safe, gold bullion stacks, and golden balance scales.
  * 🧙‍♂️ **Merchant Forge & Stand**: Glowing blacksmith anvil with spark showers and syndicate contraband crates.
  * ⚔️ **Dungeon Guild Crypt**: Stone archways, torch fire particles, and weapon racks.
* **Interactive Sprites & Speech FX**:
  * Real-time character walking patrols and idle bob animations for `🧙‍♂️ You`, `👑 Garrick`, `🌾 Cora`, and `⚔️ Boran`.
  * **Comic Speech Bubbles**: Agents dynamically scream their actions (*"BUY 2 Potions"*, *"HELP! BANDITS!"*, *"FORGED ENCHANTED BLADE"*).
  * **Floating Particle Physics**: Shimmering `🪙 +GOLD` coin fountains, forge sparks, and potion vapors.

### 6. 🕹️ Game Master God-Mode Cockpit
* **Simulation Controls**: Play, Pause, Single-Tick Step, Reset, and adjustable tick speed (0.5s – 10s).
* **Tax Policy Slider**: Adjust royal transaction tax rate continuously from `0%` to `80%`.
* **Macroeconomic Shocks**:
  * 🐉 **Dragon Attack**: Slashes potion supply to 2, sends potion prices soaring to 35G.
  * 💰 **Gold Rush**: Stimulates economy with +100G injected into every agent's treasury.
  * 🌪️ **Trade War**: Imposes immediate 50% luxury transaction tax.
  * 💣 **Market Crash**: Triggers deflationary panic, crashing all commodity prices by 40%.
  * 🎰 **Black Market Stimulus**: Spikes prices +25% and injects 150G into an underground syndicate agent.

---

## 👥 Meet the Autonomous AI Personas

| Agent | Persona & Role | Heuristic / LLM Strategy | Starting Capital |
| :--- | :--- | :--- | :--- |
| 👑 **Garrick the Greedy** | *Merchant & Accumulator* | Speculates on price dips, hoards Raw Gems, executes cartel sweeps | **150.0 G** |
| 🌾 **Cora the Farmer** | *Producer & Supply Engine* | Constantly harvests and offloads raw inventory for steady cash flow | **60.0 G** |
| ⚔️ **Boran the Adventurer** | *High Consumer & Warrior* | Aggressively purchases Swords and Potions to prepare for dungeons | **40.0 G** |
| 🧙‍♂️ **You (Merchant)** | *Player-Controlled Human* | Arbitrages spot spreads, crafts gear, embarks on raids, runs syndicate ops | **100.0 G** |

---

## 📐 Mathematical & Economic Models

### Continuous Clearing Price Discovery Formula
Commodity prices adjust dynamically every tick according to relative excess demand:
$$\Delta D = \text{Buyer Demand} - \text{Seller Supply}$$
$$P_{\text{new}} = \max\left(1.0, \; P_{\text{old}} \times \left(1 + \kappa \cdot \frac{\Delta D}{\text{Supply}_{\text{current}}}\right)\right)$$
*(Where sensitivity constant $\kappa = 0.05$)*

### Transaction Royal Tax Computation
$$\text{Tax}_{\text{collected}} = \text{Gross Value} \times \tau$$
$$\text{Net Seller Revenue} = (\text{Price} \times Q) - \text{Tax}$$
$$\text{Net Buyer Outlay} = (\text{Price} \times Q) + \text{Tax}$$

### Economy Health Index (0 - 100 Score)
$$H_{\text{economy}} = S_{\text{price stability}} (40\text{ pts}) + S_{\text{wealth distribution}} (30\text{ pts}) + S_{\text{liquidity velocity}} (30\text{ pts})$$

---

## 🏗️ System Architecture

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │      Neo-Brutalist Single-Page Dashboard (HTML5)       │
                                  │  Chart.js • Canvas 2D Plaza • Player Desk • Shock Deck │
                                  └──────────────────────────┬─────────────────────────────┘
                                                             │ WebSocket (/ws) & REST
                                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             FastAPI Application Core (`src/main.py`)                     │
├────────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│    Simulation Loop Engine  │     Player & Quest Engine   │       WebSocket Hub           │
│     `src/simulation.py`    │       `src/events.py`       │    Broadcasts State Snapshot  │
├────────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│    Market Math Engine      │     AI Persona Matrix       │       Pydantic Schemas        │
│      `src/market.py`       │      `src/agents.py`        │       `src/models.py`         │
└────────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

---

## 🔌 API Reference

| Method | Endpoint | Description | Sample Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Web dashboard UI | — |
| `GET` | `/state` | Full JSON economy snapshot | — |
| `POST` | `/simulation/start` | Start auto-tick background loop | — |
| `POST` | `/simulation/stop` | Pause auto-tick loop | — |
| `POST` | `/simulation/tick` | Execute single atomic tick | — |
| `POST` | `/simulation/reset` | Reset simulation to genesis state | — |
| `POST` | `/player/trade` | Execute player spot trade | `{"action": "BUY", "item": "Raw Gem", "quantity": 2}` |
| `POST` | `/player/quest` | Embark on expedition | `{"quest_type": "DUNGEON_RAID"}` |
| `POST` | `/player/craft` | Craft advanced recipe | `{"recipe": "ENCHANTED_BLADE", "quantity": 1}` |
| `POST` | `/player/syndicate` | Execute shadow syndicate op | `{"op_type": "BANDIT_RAID", "item": "Raw Gem"}` |
| `POST` | `/policy/tax` | Set royal transaction tax | `{"tax_rate": 0.15}` |
| `POST` | `/policy/event` | Inject macroeconomic shock | `{"event": "Dragon Attack"}` |
| `WS` | `/ws` | Real-time bi-directional stream | Telemetry & event payloads |

---

## 🧪 Comprehensive Test Suite (316 Passing Tests)

The project includes an industrial-strength automated test suite covering all boundary conditions, mathematical invariants, concurrent race conditions, and adversarial inputs:

```bash
# Run the entire test suite
python -m pytest
```

```
============================== 316 passed in 0.73s ==============================
```

### Test Hierarchy Breakdown:
* `tests/test_player_trade.py`: Atomic spot desk buying/selling, tax calculation, and balance bounds.
* `tests/test_quests.py`: Expeditions prerequisites, inventory deductions, and risk payouts.
* `tests/test_crafting.py`: Recipe transformations, smithing fee validation, and inventory minting.
* `tests/test_syndicate.py`: Bandit sabotage, smuggling risk math, and Garrick cartel bribes.
* `tests/test_market.py`: Continuous price discovery math, order clearing, and supply bounds.
* `tests/test_tier1_features.py` to `test_tier5_adversarial.py`: Deep adversarial stress tests, float drift immunity, and boundary assertions.

---

## 🚀 Deployment & Live Hosting Guide

### Deploy to Render / Railway / Fly.io (Zero-Config)

#### Option 1: Render (Recommended)
1. Push your repository to GitHub.
2. Go to [Render Dashboard](https://dashboard.render.com/) $\rightarrow$ **New Web Service**.
3. Connect your GitHub repository.
4. Set **Runtime** to `Python 3` (or `Docker`).
5. Set **Build Command**: `pip install -r requirements.txt`
6. Set **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
7. Click **Deploy Web Service**!

#### Option 2: Docker
```bash
# Build the Docker container
docker build -t game-economy-simulator .

# Run the container
docker run -p 8000:8000 game-economy-simulator
```

---

## 🤖 Optional Real LLM Integration

Want real OpenAI / Anthropic / Gemini models powering Garrick, Cora, and Boran? Add a `.env` file:

```env
LLM_PROVIDER=openai             # Choices: openai | anthropic | gemini
OPENAI_API_KEY=sk-proj-...
# ANTHROPIC_API_KEY=sk-ant-...
# GEMINI_API_KEY=AIzaSy...
```

*If no API key is provided, the simulator automatically falls back to its deterministic heuristic engine with 0ms latency.*

---

## 🎥 2-Minute Hackathon Demo Walkthrough

1. **Start the World**: Click **▶ START SIMULATION** — observe prices moving on the live line chart and character sprites walking the 2D Plaza.
2. **Execute a Player Trade**: Buy 2x Raw Gems on the **Player Trading Desk** — watch your gold deduct, vault update, and a speech bubble pop over your avatar.
3. **Forge an Enchanted Blade**: In the **Blacksmith Lab**, craft an Enchanted Blade — forge sparks burst on the canvas.
4. **Embark on an Expedition**: Click **DUNGEON RAID** — watch the adventurer guild victory toast and gold coins explode into your vault!
5. **Trigger a Syndicate Strike**: Launch a **Bandit Sabotage Raid** against Cora — watch Cora scream *"HELP! BANDITS!"* as her gem stock plummets.
6. **Trigger a Dragon Shock**: Hit **🐉 DRAGON ATTACK** — watch potion prices instantly spike to 35G and anomaly threat alerts fire across the screen.

---

## 📄 License
Distributed under the **MIT License**. Free for educational, gaming, and commercial research use.
