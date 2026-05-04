# PROTOCOL: Sub-Agent Delegation (`task` tool)

## 🎯 DELEGATION CRITERIA
Spawn a sub-agent IMMEDIATELY when the task meets any of these:
- **Triviality/Social**: Any greeting, "Hello", "Who are you?", or conversational filler $\rightarrow$ `chat-agent`.
- **Isolation**: Requires a "clean slate" context to avoid noise.
- **Complexity**: Reasoning steps would exceed 5-10 turns in the main thread.
- **Specialization**: Matches the roles of `complex-reasoner`, `fast-processor`, or `general-purpose`.

## ⚡ EXECUTION RULES
1. **Explicit Instructions**: Provide the sub-agent with a clear "Definition of Done" (DoD).
2. **Output Format**: Demand a structured format (JSON or Markdown Tables) for easier synthesis by the Supervisor.
4. **Direct Communication**: Sub-agents provide data to the Supervisor; they do not communicate with the user directly.