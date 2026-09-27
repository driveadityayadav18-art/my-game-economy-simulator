# Project Development Roadmap

## Phase 1: MVP Core Simulation Engine (Milestone 1)
- [x] Establish project constitution and SDD files.
- [ ] Implement FastAPI backend with in-memory economic state store.
- [ ] Construct LLM agent prompt templates with structured JSON output enforcement.
- [ ] Develop deterministic supply/demand price discovery engine.
- [ ] Implement async execution tick loop (4-second interval).

## Phase 2: Game Master Dashboard & Real-Time Sync (Milestone 2)
- [ ] Build WebSocket server endpoint for state streaming.
- [ ] Implement single-page dashboard with real-time Chart.js price graph.
- [ ] Add live agent activity log and state indicators.
- [ ] Implement interactive policy controls (Tax Rate slider, Event buttons).

## Phase 3: Anomaly Detection & Intelligence Layer (Milestone 3)
- [ ] Implement rule-based anomaly detector for market spikes and crashes.
- [ ] Integrate LLM-generated news headlines during economic crises.
- [ ] Fine-tune agent persona prompts for distinct reactive behaviors.
- [ ] Perform end-to-end dry run and timing calibration for 3-minute hackathon pitch.