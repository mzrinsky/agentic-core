import subprocess
import os
import time
import requests
from typing import Dict, Optional
from src.config.loader import ConfigLoader

class ServerManager:
    def __init__(self, model_configs: Optional[Dict] = None):
        # Configuration for the llama-server
        self.bin_path = "llama-server"
        # Map of model identifiers to their filesystem paths and configs
        # Expected format: {"model_id": {"path": "...", "ctx_size": 16384}}
        self.model_configs = model_configs or {}
        self.current_model = None
        self.process = None
        self.port = 8080
        self.template_path = "/home/scrub/models/templates/google-gemma-4-31B-it.jinja"
        self.config = ConfigLoader()
        self.log_file_path = "server_runtime.log"

    def _log(self, level: int, message: str, color_code: int):
        # Color mapping:
        colors = {
            0: "\033[91m", # Red
            1: "\033[93m", # Yellow
            2: "\033[94m", # Blue
            3: "\033[38;5;254m", # Gray/Off-white
            4: "\033[92m", # Green
        }
        color = colors.get(color_code, "")
        reset = "\033[0m"
        if self.config.get_log_level() >= level:
            print(f"{color}[ServerManager] {message}{reset}")

    def _stop_server(self):
        if self.process:
            self._log(3, f"Stopping server for model {self.current_model}...", 2)
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            self.current_model = None

    def _wait_for_server(self, timeout=60):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://localhost:{self.port}/health", timeout=2)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        return False

    def ensure_model(self, model_id: str):
        """
        Ensures the server is running the correct model and config.
        """
        # Compare current state with requested state
        # We only restart if the model_id changed or a critical runtime param changed
        if self.current_model == model_id and self.process and self.process.poll() is None:
            return 

        spec = self.model_configs.get(model_id)
        if not spec:
            raise ValueError(f"No config spec found for model {model_id}")

        self._stop_server()
        
        # Construct CLI command using config spec + runtime params
        cmd = [
            self.bin_path,
            "-m", spec["path"],
            "--port", str(self.port),
            "--ctx-size", str(spec.get("ctx_size", 16384)),
            "--chat-template-file", spec.get("template", ""),
        ]
        
        # Add model-specific flags (min-p, etc) from the config loader
        cmd.extend(spec.get("extra_flags", []))

        # Handle output redirection based on log level
        log_level = self.config.get_log_level()
        if log_level >= 4:
            out_file = open(self.log_file_path, "w")
            stderr_dest = subprocess.STDOUT
        else:
            out_file = subprocess.DEVNULL
            stderr_dest = subprocess.DEVNULL

        self._log(3, f"Starting server for model {model_id}...", 2)

        self.process = subprocess.Popen(
            cmd, stdout=out_file, stderr=stderr_dest
        )
        self.current_model = model_id
        
        time.sleep(1)
        # Check if process crashed immediately
        poll_result = self.process.poll()
        if poll_result is not None:
            self._log(0, f"Critical: Server process exited immediately with code {poll_result}", 0)
            if log_level >= 4 and out_file != subprocess.DEVNULL:
                out_file.close()
            raise RuntimeError(f"Server failed to start for model {model_id}")

        if not self._wait_for_server():
            self._log(0, f"Critical: Server failed to respond to health check for model {model_id}", 0)
            # Ensure we don't leave a zombie process
            self._stop_server()
            if log_level >= 4 and out_file != subprocess.DEVNULL:
                out_file.close()
            raise TimeoutError(f"Server failed to start for model {model_id}")
        
        self._log(3, f"Server successfully started: {model_id}", 4)


    def stop(self):
        self._stop_server()

# Singleton instance
server_manager = ServerManager()