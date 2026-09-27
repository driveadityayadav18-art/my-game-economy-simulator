# 🎤 Hackathon Demo Script — AI-Driven Game Economy Simulator
**Duration:** ~2 minutes  
**Audience:** Judges  
**Goal:** Show a live, interactive, AI-driven economy — make it feel real

---

## 🚀 Before You Start

```bash
python -m uvicorn src.main:app --reload --port 8000
```
Open `http://localhost:8000` — confirm the dashboard loads.  
Speed slider at **4.0s** (default). Tax at **10%**.

---

## 📋 Step-by-Step Script

---

### Step 1 — Set the Scene (15 sec)

> *"What you're looking at is a live AI-powered game economy. Three autonomous agents — Garrick the Greedy, Cora the Farmer, and Boran the Adventurer — are trading three commodities in real time. Each agent has a distinct personality and makes decisions every few seconds."*

👉 Point to the **3 agent cards** (top right).  
👉 Point to the **price chart** (top left) — lines are flat, sim is paused.

---

### Step 2 — Start the Economy (20 sec)

> *"Let me start the simulation."*

👉 Click **▶ Start**

> *"You can see prices starting to move. The price formula is supply-and-demand — if agents buy more than they sell, price goes up; if they sell more, it drops. No hardcoded values, it's all emergent."*

👉 Point to the **price chart lines moving**.  
👉 Point to the **Agent Thoughts panel** — *"Each agent is reasoning out loud. Garrick says he's buying cheap to sell later. Cora is steadily selling Raw Gems. Boran just bought a Health Potion for the thrill."*

---

### Step 3 — Dragon Attack (20 sec)

> *"Now let me trigger an economic shock."*

👉 Click **🐉 Dragon Attack**

> *"A dragon has attacked. Health Potion supply just crashed to 2 units and the price spiked to 35 Gold. Watch the chart."*

👉 Point to the **blue line spiking** on the price chart.  
👉 Point to the **📰 Market Intelligence** panel — a SPIKE alert will appear.  
👉 Point to **Boran's thought** — he's trying to buy potions but can't afford them.

---

### Step 4 — Gold Rush (15 sec)

> *"Now let's inject capital into the economy."*

👉 Click **💰 Gold Rush**

> *"Every agent just got 100 Gold. Watch the wealth leaderboard."*

👉 Point to the **💰 Wealth Leaderboard** — all three bars jump simultaneously.  
👉 Point to **Boran** — *"He's now buying potions aggressively with his new gold."*

---

### Step 5 — Tax Policy (15 sec)

> *"Our Game Master can also adjust policy. Let me raise the transaction tax."*

👉 Drag the **Tax Slider to 80%**

> *"At 80% tax, every trade becomes expensive. Watch the Activity Log — you'll see more REJECTED and HOLD actions. The Health Score in the header just dropped."*

👉 Point to the **❤️ Health Score** turning yellow or red.  
👉 Point to the **📋 Activity Log** — more HOLD entries appearing.

---

### Step 6 — Market Crash (15 sec)

> *"One more event — a full market crash."*

👉 Click **💣 Market Crash**

> *"All prices just dropped 40%. Bargain hunters incoming."*

👉 Point to all 3 lines **dropping sharply** on the chart.  
👉 **CRASH** alerts should appear in the Market Intelligence feed.

---

### Step 7 — Reset (10 sec)

> *"And the key thing for a game — any game master can reset the whole economy instantly for a new run."*

👉 Click **🔄 Reset**

> *"Tick 0. Clean slate. Every run tells a different story depending on which events you trigger and when."*

---

## 🎯 Closing Line

> *"This is a fully functioning multi-agent AI economy — real-time pricing, autonomous decision-making, policy controls, anomaly detection, and a live dashboard. Built in 12 hours. No external infrastructure required — just run it."*

---

## ⚠️ Backup Moves (If Something Looks Off)

| Issue | Fix |
|-------|-----|
| Prices not moving | Confirm ▶ Start was clicked, check status dot is green |
| Agent thoughts empty | Wait 1 tick — they populate after first decision |
| Health score stuck at `—` | Trigger a manual ⏭ Tick first |
| WebSocket disconnected | Page auto-reconnects in 3s, wait it out |
| Chart lines flat | Drag speed slider left to speed up ticks |

---

## 🏁 Feature Checklist (Before Demo)

- [ ] Server running on `localhost:8000`
- [ ] Dashboard loads, status dot is green
- [ ] Click ▶ Start — prices move within 5 seconds
- [ ] Dragon Attack fires — HP price goes to ~35G
- [ ] Gold Rush fires — all wealth bars jump
- [ ] Health Score updates in header
- [ ] Agent Thoughts panel populated
- [ ] Reset works — tick goes to 0, chart clears
