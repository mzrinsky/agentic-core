import redis
import json
import time
from typing import Optional, Dict, Any
import os

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
QUEUE_NAME = "agentic_core_tasks"
SCHEDULED_SET = "agentic_core_scheduled"
RETRY_QUEUE = "agentic_core_retries"

class TaskQueue:
    def __init__(self):
        self._lua_pop_scheduled = None # Initialize as None
        try:
            self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            self.r.ping()
            # Define the Lua script for atomic "fetch and remove" from sorted set
            self._lua_pop_scheduled = self.r.register_script("""
                local task = redis.call('zrangebyscore', KEYS[1], 0, ARGV[1])
                if #task > 0 then
                    redis.call('zrem', KEYS[1], task[1])
                    return task[1]
                end
                return nil
            """)
        except redis.ConnectionError:
            print("\033[93m[Queue] Warning: Redis connection failed. Queue will be unavailable.")


    def push_task(self, task_data: Any, delay_seconds: int = 0, retry_count: int = 0):
        """
        Pushes a task into the queue. Now supports retry_count.
        """
        payload = {
            "data": task_data,
            "timestamp": time.time(),
            "scheduled_for": time.time() + delay_seconds,
            "retries": retry_count
        }
        payload_json = json.dumps(payload)

        if not hasattr(self, 'r') or self._lua_pop_scheduled is None:
            print("[Queue] Error: Redis not connected. Cannot push task.")
            return

        if delay_seconds > 0:
            self.r.zadd(SCHEDULED_SET, {payload_json: payload['scheduled_for']})
            print(f"[Queue] Scheduled task: {task_data}")
        else:
            self.r.lpush(QUEUE_NAME, payload_json)
            print(f"[Queue] Pushed immediate task: {task_data}")

    def pop_task(self) -> Optional[Dict[str, Any]]:
        """
        Checks for immediate tasks or overdue scheduled tasks atomically.
        """
        if not hasattr(self, 'r') or self._lua_pop_scheduled is None:
            return None
        # 1. Atomic fetch from scheduled set using Lua
        now = time.time()
        task_json = self._lua_pop_scheduled(keys=[SCHEDULED_SET], args=[now])
        
        if task_json:
            return json.loads(task_json)

        # 2. Standard pop from immediate queue
        task_json = self.r.rpop(QUEUE_NAME)
        if task_json:
            return json.loads(task_json)

        return None
        
# Singleton instance for the agent to use
agent_queue = TaskQueue()