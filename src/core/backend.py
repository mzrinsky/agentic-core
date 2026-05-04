from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
import os

def create_agent_backend(memories_dir: str = None, skills_dir: str = None, workspace_dir: str = None):
    """
    Configures a heterogeneous backend for the Agentic OS.
    """
    # Rooting everything under the 'agent/' directory by default
    mem_path = os.path.abspath(memories_dir) if memories_dir else os.path.abspath("./agent/memories")
    skl_path = os.path.abspath(skills_dir) if skills_dir else os.path.abspath("./agent/skills")
    wrk_path = os.path.abspath(workspace_dir) if workspace_dir else os.path.abspath("./agent/workspace")
    
    os.makedirs(mem_path, exist_ok=True)
    os.makedirs(skl_path, exist_ok=True)
    os.makedirs(wrk_path, exist_ok=True)

    return CompositeBackend(
        default=StateBackend(), 
        routes={
            "/memories/": FilesystemBackend(root_dir=mem_path, virtual_mode=True),
            "/skills/": FilesystemBackend(root_dir=skl_path, virtual_mode=True),
            "/workspace/": FilesystemBackend(root_dir=wrk_path, virtual_mode=True),
        }
    )