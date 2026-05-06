import os
import yaml

class ConfigLoader:
    """
    Handles the loading of chat style, reasoning, and agent blueprints
    from the configuration directory.
    """
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = config_dir

    def load_file(self, filename: str, default: str = "") -> str:
        path = os.path.join(self.config_dir, filename)
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            print(f"Error loading {path}: {e}")
        return default

    def get_all_blueprints(self) -> dict:
        return {
            "system": self.load_file("SYSTEM-PROMPT.md", "You are the Agentic Core."),
            "user": self.load_file("USER-PROFILE.md", ""),
            "chat_style": self.load_file("CHAT-PROMPT.md", ""),
            "complex": self.load_file("COMPLEX-REASONING.md", ""),
            "fast": self.load_file("FAST-PROCESSOR.md", ""),
            "task_protocol": self.load_file("TASK-PROMPT.md", ""),
            "skills_protocol": self.load_file("SKILLS-PROMPT.md", ""),
            "files_protocol": self.load_file("FILESYSTEM-PROMPT.md", ""),
        }

    def get_log_level(self) -> int:
        """
        Returns the system log level. 
        Priority: Environment Variable -> Default (2)
        """
        try:
            return int(os.getenv("AGENT_LOG_LEVEL", 2))
        except (ValueError, TypeError):
            return 2

    def load_yaml(self, filename: str, default: dict = {}) -> dict:
        path = os.path.join(self.config_dir, filename)
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or default
        except Exception as e:
            print(f"Error loading YAML {path}: {e}")
        return default

    def get_mcp_configs(self, agent_config_dir: str = "./agent/config") -> dict:
        """
        Combines MCP tool configs from system root and agent directory.
        """
        system_mcp = self.load_yaml("mcp-tools.yaml")
        
        # Load from agent/config/mcp-tools.yaml
        agent_config_path = os.path.join(agent_config_dir, "mcp-tools.yaml")
        agent_mcp = {}
        try:
            if os.path.exists(agent_config_path):
                with open(agent_config_path, "r", encoding="utf-8") as f:
                    agent_mcp = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading agent MCP config {agent_config_path}: {e}")

        # Merge dictionaries (system configs override agent configs if keys collide)
        return {**agent_mcp, **system_mcp}

    def get_model_paths(self) -> dict:
        """
        Returns a mapping of model identifiers to their 
        physical server requirements.
        """
        return {
            "gemma-4-4b": {
                "path": "data/models/google_gemma-4-E4B-it-Q5_K_M.gguf",
                "ctx_size": 8192,
                "template": "data/templates/google-gemma-4-31B-it.jinja",
                "extra_flags": ["--flash-attn", "on", "--gpu-layers", "auto", "--jinja", "--reasoning", "on", "--reasoning-format", "deepseek", "--min-p", "0.05"]
            },
            "gemma-4-26b": {
                "path": "data/models/google_gemma-4-26B-A4B-it-Q5_K_M.gguf",
                "ctx_size": 16384,
                "template": "data/templates/google-gemma-4-31B-it.jinja",
                "extra_flags": ["--flash-attn", "on", "--gpu-layers", "auto", "--jinja", "--reasoning", "on", "--reasoning-format", "deepseek", "--min-p", "0.05", "--repeat-penalty", "1.1"]
            },
            "gemma-4-31b": {
                "path": "data/models/google_gemma-4-31B-it-Q5_K_M.gguf",
                "ctx_size": 32768,
                "template": "data/templates/google-gemma-4-31B-it.jinja",
                "extra_flags": ["--flash-attn", "on", "--gpu-layers", "auto", "--jinja", "--reasoning", "on", "--reasoning-format", "deepseek", "--min-p", "0.05"]
            },
        }