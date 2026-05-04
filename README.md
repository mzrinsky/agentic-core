Apply
# Agentic Core

> [!IMPORTANT]
> **Personal Lab & Dogfooding:** This is a personal project built for my own use. I am "dogfooding" this architecture by using it as the engine to build and run agents for my other real-world projects. I've made this repository public for those interested in the implementation patterns, but it is primarily an evolving toolkit for my own agency needs.

Agentic Core is a **reference implementation** of a high-agency, context-aware operational environment built upon the `deepagents` framework. Rather than a static application, it serves as a foundational blueprint for transitioning traditional "Chat" interactions into "Agency"—enabling a system capable of perceiving state, planning multi-step sequences, and managing its own persistence and scheduling.


## 🎯 Project Vision
The goal of Agentic Core is to provide a plug-and-play architecture that demonstrates how to move from reactive prompting to active goal management. By utilizing a `Trigger → Action → Reflection → Schedule` loop via Redis, this implementation showcases a production-ready pattern for executing complex workflows autonomously.

While this project is pre-configured for the **Gemma 4** family and **llama-server**, the decoupled nature of the `deepagents` framework allows this setup to be used as a base for any custom agentic environment and supports any **OpenAI** / **LangChain** compatible server.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Active](https://img.shields.io/badge/Status-Active-green.svg)]()
[![Tech Stack](https://img.shields.io/badge/Python%203.10+-blue.svg)]()

## 🤖 Development Methodology: Human-in-the-Loop AI

This project is developed using a **Human-in-the-Loop (HITL)** approach to AI augmentation:

*   **Architecture & Planning**: The high-level system design and technical specifications are co-authored by humans and AI to ensure rigorous structural integrity.
*   **Implementation**: The codebase is primarily AI-generated, guided by the strict constraints defined in `AGENTS.md`, and refined through human review and manual edits.
*   **Attribution**: Every commit is strictly tagged with the contributing AI model and parameter count (e.g., Co-authored-by: Gemma 4 31B) to maintain a transparent audit trail of human vs. AI contributions.

## 🛠 Technical Architecture

### 🧠 Model Orchestration
This implementation demonstrates a dynamic routing strategy across different model sizes to balance latency and intelligence. This pattern can be adapted to any model family:
- **Triage/Fast Processing:** (e.g., Gemma 4 4B) Rapid data extraction and context analysis.
- **General Execution:** (e.g., Gemma 4 26B) Standard research and multi-step tasks.
- **Complex Architecture:** (e.g., Gemma 4 31B) High-precision technical synthesis and debugging.

### 🏗 System Components
- **Agent Factory:** A modular system that assembles the Supervisor and specialized sub-agents.
- **Config Loader:** A dynamic blueprint system that separates chat style and reasoning protocols from the core logic via external markdown files.
- **Worker Loop:** The "Nervous System" that polls a Redis task queue, processing inputs and streaming reasoning/tool calls in real-time.
- **Interface Layer:** A decoupled interface (currently Discord) that pushes user intentions into the task queue, allowing for easy swapping of the UI.
- **Memory Strategy:** 
  - *Ephemeral:* Session-based state management.
  - *Persistent:* Long-term project knowledge stored in `/memories/`.

### 🛠 Tooling & Skills
- **On-Demand Skills:** Skills are loaded via metadata matching, allowing the agent to expand its capabilities dynamically.
- **System Tools:** Built-in primitives for task scheduling, human intervention requests, and external notifications.

## 📂 Project Structure

```text
.
├── agent/
│   ├── skills/        # Plugin-style agent-generated skills loaded via metadata
│   ├── memories/      # Long-term persistent project knowledge
│   └── workspace/     # Sandbox area for agent-generated files
├── config/            # Markdown blueprints for subagents & protocols
│   ├── SYSTEM-PROMPT.md
│   ├── USER-PROFILE.md
│   ├── CHAT-PROMPT.md
│   ├── COMPLEX-REASONING.md
│   ├── FAST-PROCESSOR.md
│   ├── TASK-PROMPT.md
│   └── SKILLS-PROMPT.md
├── skills/            # Plugin-style skills loaded via metadata
├── dead_letter/       # Failed task queue for debugging and reflection
└── ...                # Core engine and infrastructure logic
```

## 📜 Law of Attribution
To maintain a transparent audit trail, every contribution is tracked via a strict taxonomy in commit footers:
- `Co-authored-by: [Model Name] [Parameter Count]` (For AI-generated logic/fixes)
- `Generated-by: [Model Name] [Parameter Count]` (For fully automated end-to-end tasks)

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Redis Server
- LLM Server (contains LlamaServerAdapter, which can run a local `llama-server`, but will work with any OpenAI compatible server)
- Discord Bot Token (Optional)

### Installation
```bash
# check out the repo..
# Install dependencies
uv sync
```

### Configuration
Set up your environment variables in a `.env` file or your shell (see `.env.example`):

```bash
# LLM Configuration
export LLM_BASE_URL="http://localhost:8080"
export LLM_API_KEY="your_api_key"

# Infrastructure
export REDIS_HOST="localhost"
export REDIS_PORT=6379

# Interface
export DISCORD_BOT_TOKEN="your_token_here"

# ServerManager (run local llama-server)
export MANAGE_SERVER="true"
```

### Running Infrastructure
The project includes a `docker-compose.yaml` to quickly spin up the required Redis instance:

```bash
docker-compose -f docker/docker-compose.yaml up -d
```

## ⚙️ LLM Backend & Routing
The system is designed to be model-agnostic. The current implementation utilizes a `ServerManager` to handle the lifecycle of local LLM instances. It is a convenience feature to provide local model swapping while utilizing the latest `llama-server` which is typically the most up to date.

It is controllable via. command line argument `--no-manage-server` and env var `MANAGE_SERVER` and internally uses an OpenAI compatible LangChain `ChatModel`.

**Note:** The `ServerManager` is currently a stop-gap convenience feature. The architecture is designed to migrate toward high-performance routing servers (such as those integrated into `llama-server` or professional inference gateways) that handle request queuing and model swapping natively.

### Model Orchestration
- **SwappableLLM:** The abstraction layer allowing the agent to switch between different backends without changing core logic.
- **LlamaServerAdapter:** The specific bridge for OpenAI-compatible APIs.

## 📖 Usage

### 1. Starting the Agent Worker
The core engine processes tasks from the Redis queue. You can launch it directly via `main.py`:

```bash
# Basic start
python src/main.py

# Start with verbose logging (Level 3: Debug) and disable automatic server management
python src/main.py --log-level 3 --no-manage-server
```

**Log Level Reference:**
- `0`: Errors only
- `1`: Basic
- `2`: Verbose (Default)
- `3`: Debug
- `4`: Trace

### 2. Injecting Tasks
You can interact with the agent through two primary channels:

**A. Discord Interface:**
When you run `main.py`, the system automatically initializes the Discord bot. Any messages sent to the bot are pushed into the Redis queue for the worker to process.

**B. CLI Tool:**
Push instructions directly into the queue, bypassing the UI for administrative tasks.

**Immediate Execution:**
```bash
./bin/cli "Analyze the current project structure and summarize the memory strategy in /agent/memories/summary.md"
```

**Scheduled Execution:**
Use the `--delay` flag to schedule a task for the future (in seconds):
```bash
./bin/cli "Run a system health check on the Redis connection" --delay 3600
```
