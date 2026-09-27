# Quickstart Guide: Running the Simulator

## Prerequisites
- Python 3.11+
- OpenAI API Key (or Anthropic API Key)

## Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/your-username/ai-game-economy-simulator.git
   cd ai-game-economy-simulator
   ```

2. Install backend dependencies:
   ```bash
   pip install fastapi uvicorn openai websockets
   ```

3. Export your API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

4. Launch the simulation server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

5. Open the control dashboard in your browser:
   ```text
   http://localhost:8000
   ```