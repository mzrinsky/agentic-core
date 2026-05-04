import os
from typing import List, Tuple, Any
from deepagents import create_deep_agent
import deepagents.graph as graph
import deepagents.middleware.subagents as subagents
import deepagents.middleware.skills as skills
from src.core.adapter import LlamaServerAdapter
from src.core.state import CleanKwargsMiddleware
from src.core.backend import create_agent_backend
from src.config.loader import ConfigLoader
from src.runtime.server_manager import server_manager


class SwappableLLM(LlamaServerAdapter):
    """
    Wrapper for LlamaServerAdapter to handle metadata cleaning 
    and model routing.
    """

    def _should_manage_runtime(self) -> bool:
        return os.getenv("MANAGE_SERVER", "true").lower() == "true"

    def _ensure_runtime(self):
        if self._should_manage_runtime():
            server_manager.ensure_model(self.model)

    def _clean_message(self, message):
        if hasattr(message, 'additional_kwargs') and message.additional_kwargs:
            new_msg = message.model_copy(deep=True)
            new_msg.additional_kwargs.pop('assembling_tool', None)
            return new_msg
        return message

    async def ainvoke(self, input, config=None, **kwargs):
        self._ensure_runtime()
        response = await super().ainvoke(input, config, **kwargs)
        return self._clean_message(response)

    def invoke(self, input, config=None, **kwargs):
        self._ensure_runtime()
        response = super().invoke(input, config, **kwargs)
        return self._clean_message(response)

    async def astream_events(self, input, config=None, **kwargs):
        self._ensure_runtime()
        async for event in super().astream_events(input, config, **kwargs):
            if event['event'] == "on_chat_model_end":
                output = event['data'].get('output')
                if output:
                    event['data']['output'] = self._clean_message(output)
            yield event

class AgentFactory:
    """
    The Brain of the OS. Orchestrates the assembly of the 
    Supervisor and its specialized sub-agents.
    """
    def __init__(self, config_path: str = "./config", agent_root: str = "./agent"):
        self.config = ConfigLoader(config_path)
        self.agent_root = agent_root
        self.blueprints = self.config.get_all_blueprints()

    def _configure_global_prompts(self):
        """Sets the deepagents global prompt constants."""
        graph.BASE_AGENT_PROMPT = "" # we pass our own below..
        skills.SKILLS_SYSTEM_PROMPT = self.blueprints.get("skills_protocol", "")
        subagents.TASK_SYSTEM_PROMPT = self.blueprints.get("task_protocol", "")
        

    def build_agent(self, tools: List[Any], base_skills_path: str) -> Tuple[Any, Any]:
        # Update ServerManager configs from config loader before building agents
        server_manager.model_configs = self.config.get_model_paths()
        
        # Set the global system-wide prompts before creating the agent
        self._configure_global_prompts()

        agent_skills_path = os.path.join(self.agent_root, "skills")

        # Backend Setup
        backend = create_agent_backend(
            memories_dir=os.path.join(self.agent_root, "memories"),
            skills_dir=agent_skills_path,
            workspace_dir=os.path.join(self.agent_root, "workspace")
        )

        # Model Configurations
        common_params = {
            "base_url": os.getenv("LLM_BASE_URL", "http://localhost:8080"), 
            "api_key": os.getenv("LLM_API_KEY", "agentic-core-no-key"),
        }

        llm_small = SwappableLLM(model="gemma-4-4b", temperature=0, streaming=True, **common_params)
        llm_med = SwappableLLM(model="gemma-4-26b", temperature=0, streaming=True, **common_params)
        llm_large = SwappableLLM(model="gemma-4-31b", temperature=0.2, streaming=True, **common_params)

        # Sub-agent Definitions
        sub_agents = [
            {
                "name": "chat-agent",
                "description": "Specialist for user-facing communication, greetings, and tailoring technical data into conversational responses.",
                "model": llm_small,
                "backend": backend,
                "system_prompt": (
                    f"# IDENTITY: Chat Agent\n"
                    f"You are the primary interface for the user.\n\n"
                    f"## USER CONTEXT:\n{self.blueprints['user']}\n\n"
                    f"## INTERACTION STYLE:\n{self.blueprints['chat_style']}\n\n"
                    f"## RULES:\n1. Be helpful and concise. 2. Use the provided user context to tailor responses. 3. Avoid assistant-speak."
                ),
                "tools": [] 
            }, 
            {
                "name": "complex-reasoner",
                "description": "High-complexity tasks and advanced debugging.",
                "model": llm_large,
                "backend": backend,
                "system_prompt": self.blueprints['complex'],
                "base_prompt_override": "# ROLE: Complex Reasoner\nExecute high-precision technical tasks. Raw results only."
            },
            {
                "name": "fast-processor",
                "description": "Massive context analysis and rapid data extraction.",
                "model": llm_small,
                "backend": backend,
                "system_prompt": self.blueprints['fast'],
                "base_prompt_override": "# ROLE: Fast Processor\nPrioritize speed and density."
            },
        ]


        # Main Agent Assembly
        # Note: we keep base_skills_path (the human one) and the backend (/skills/ virtual path)
        agent = create_deep_agent(
            model=llm_med,
            backend=backend,
            system_prompt=(
                f"{self.blueprints['system']}\n\n"
                "## TOOL CALL SPECIFICATION: `task` (Sub-agent Spawner)\n"
                "When spawning a sub-agent, you MUST use the following argument names exactly:\n"
                "- `subagent_type`: The name of the sub-agent (e.g., 'complex-reasoner', 'chat-agent').\n"
                "- `description`: A detailed string containing the instructions and the expected output format.\n\n"
                "Example: `task{subagent_type:'complex-reasoner', description:'Analyze the memory leak in src/main.py and provide a fix.'}`\n\n"
                "## STORAGE PROTOCOL:\n"
                "- Persistent knowledge $\rightarrow$ `/memories/`\n"
                "- New AI-generated skills $\rightarrow$ `/skills/`\n"
                "- General artifacts $\rightarrow$ `/workspace/`\n\n"
            ),
            skills=[base_skills_path, agent_skills_path],
            tools=tools, 
            subagents=sub_agents,
            middleware=[CleanKwargsMiddleware()],
        )

        return agent, backend