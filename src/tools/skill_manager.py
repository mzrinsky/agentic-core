import os
from typing import List, Optional
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

class SkillManager:
    """
    Manages the configuration and paths for DeepAgent skills.
    Ensures that the Agentic OS adheres to the 'Progressive Disclosure' 
    pattern defined in the DeepAgents specification.
    """
    
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        # Define the standard paths for skill layering (User -> Project)
        self.skill_paths = [
            os.path.join(os.path.expanduser("~"), ".deepagents/skills/"),
            os.path.join(self.root_dir, "skills/"),
        ]

    def get_skill_sources(self) -> List[str]:
        """
        Returns the list of paths to be passed to the create_deep_agent 
        'skills' parameter. Order matters: last one wins.
        """
        # Only return paths that actually exist on disk to avoid SDK warnings
        return [path for path in self.skill_paths if os.path.exists(path)]

    def configure_agent_backend(self, **agent_kwargs):
        """
        Injects the skill configuration into the agent's initialization arguments.
        
        Args:
            agent_kwargs: The dictionary of arguments passed to create_deep_agent
        """
        # Set the skills paths for the agent
        agent_kwargs["skills"] = self.get_skill_sources()
        
        # Ensure we are using FilesystemBackend for local OS operation
        if "backend" not in agent_kwargs:
            agent_kwargs["backend"] = FilesystemBackend(root_dir=self.root_dir)
            
        return agent_kwargs
