# Agentic Core: Operational Manifesto

## 🎯 Project Vision
To build a high-agency, context-aware operating environment utilizing the `deepagents` framework. The goal is to transition from "Chat" to "Agency"—enabling the system to perceive state, plan multi-step sequences, and manage its own persistence and scheduling.

## 🛠 Technical Architecture
- **Autonomous Loop:** `Trigger → Action → Reflection → Schedule` via Redis.
- **Model Orchestration:** Dynamic routing between Gemma 4 model sizes (e.g., 26B for triage, 31B for complex architecture).
- **Memory Strategy:** 
  - *Ephemeral:* Session-based state.
  - *Persistent:* Long-term project knowledge stored in `/memories/`.
- **Skill Loading:** On-demand loading via metadata matching.

## 📜 Law of Attribution
To maintain a transparent audit trail of human vs. AI contributions, every commit must include a footer identifying the AI's role using the following strict taxonomy:

### Case A: AI-Generated Code/Logic
Used when the AI wrote the actual code, implemented a feature, or fixed a bug.
**Format:** `Co-authored-by: [Model Name] [Parameter Count]`
*Example: `Co-authored-by: Gemma 4 31B`*

### Case B: Fully AI-Automated
Used when the AI performed the task end-to-end via Agent Mode.
**Format:** `Generated-by: [Model Name] [Parameter Count]`
*Example: `Generated-by: Gemma 4 31B`*

**Requirement for Models:** The model must accurately identify its own identity and parameter count based on its current system prompt or known architecture.