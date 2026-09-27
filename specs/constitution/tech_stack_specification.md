# Tech Stack & Architectural Guidelines

## 1. Stack Components

| Layer | Technology | Selection Rationale |
| :--- | :--- | :--- |
| **Frontend** | Single-page HTML5, TailwindCSS, JavaScript (ES6+) | Zero setup overhead, instantaneous loading, easy single-file build for hackathon presentation. |
| **Visualization** | Chart.js | Lightweight, responsive real-time line charts for tracking item prices and wealth distribution. |
| **Backend API Engine** | Python 3.11+, FastAPI, Uvicorn | High performance asynchronous execution required for parallel LLM API calls and WebSocket streaming. |
| **Real-time Transport** | WebSockets (`/ws`) | Bidirectional low-latency state synchronization between simulation engine and UI. |
| **LLM Integration** | OpenAI API (`gpt-4o-mini`) or Anthropic API (`claude-3-5-haiku`) | Structured JSON outputs, high speed, low cost per tick. |
| **State Storage** | In-Memory Data Structures (Python Dicts) | Maximized execution speed for live demo without database bottleneck. |

## 2. Architectural Constraints & Non-Negotiables
- **Strict JSON Parsing:** All agent LLM calls must enforce JSON schema outputs to prevent simulation crashes due to malformed text.
- **Parallel Execution:** Agent reasoning steps per tick MUST execute asynchronously via `asyncio.gather()` to keep tick latency under 2 seconds.
- **Fail-Safe Fallbacks:** If an LLM call fails or times out (over 2.5 seconds), the agent must default to a `"HOLD"` action with a logged reason.
- **Decoupled Pricing Engine:** The market price formula must be mathematical and deterministic, influenced by agent transaction volumes rather than arbitrary LLM decisions.