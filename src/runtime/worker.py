import asyncio
from datetime import datetime
from langchain_core.messages import AIMessageChunk, AIMessage
from src.runtime.queue import agent_queue
from src.config.loader import ConfigLoader
import os
import json
import traceback

MAX_RETRIES = 3
DLQ_ENABLED = True  # Feature flag for Dead Letter Queue persistence
DLQ_DIR = "dead_letter"

DEBUG_LOG_FILE = "agentic_core_debug.log"

# Initialize config for log level access
config = ConfigLoader()
LOG_LEVEL = config.get_log_level()

def debug_log_chunk(event: dict):
    """Logs raw chunk data to a file for debugging."""
    if LOG_LEVEL < 4:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    try:
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            log_entry = f"[{timestamp}] {repr(event)}\n{'-'*40}\n"
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write to debug log: {e}")

async def process_task(agent, task_id, task_data):
    """
    Processes a single task from the queue. 
    If task_data is a dict, it synthesizes a prompt to ensure the agent 
    sees all relevant metadata.
    """
    # Synthesize the user input string from structured data if necessary
    if isinstance(task_data, dict):
        # Converts the dict into a clean "Key: Value" list
        formatted_meta = "\n".join([f"{k}: {v}" for k, v in task_data.items()])
        user_input = f"Structured Task Data:\n{formatted_meta}"
    else:
        user_input = str(task_data)

    if LOG_LEVEL >= 2:
        print(f"\n\033[38;5;254m[Worker] Processing Task [{task_id}]: {user_input}")
    
    reasoning = False
    forming_toolcall = False
    config = {"recursion_limit": 250}
    async for event in agent.astream_events({"messages": [("user", user_input)]}, config=config, version="v2"):
        debug_log_chunk(event)
        event_type = event['event']
        
        if event_type == "on_chat_model_stream":
            chunk = event['data']['chunk']
            if not isinstance(chunk, AIMessageChunk):
                continue

            if LOG_LEVEL >= 3:
                # Handle Reasoning (Thinking)
                reasoning_chunk = chunk.additional_kwargs.get("reasoning")
                if reasoning_chunk:
                    reasoning = True
                    print(f"\033[90m{reasoning_chunk}\033[0m", end="", flush=True)

            # Handle Tool Assembly - Preserving original ANSI colors
            tool_chunk = chunk.additional_kwargs.get("assembling_tool")
            if tool_chunk:
                if not forming_toolcall and reasoning:
                    reasoning = False
                    forming_toolcall = True
                    print("\n", end="", flush=True)

                for event_item in tool_chunk:
                    if event_item.get('type') == "token":
                        print(f"\033[38;5;230m{event_item.get('value')}\033[0m", end="", flush=True)

            # Handle Final Content
            if LOG_LEVEL >= 1 and chunk.content and not reasoning_chunk:
                if reasoning or forming_toolcall:
                    forming_toolcall = False
                    reasoning = False
                    print("\n", end="", flush=True)
                print(chunk.content, end="", flush=True)

        elif event_type == "on_chat_model_end":
            if LOG_LEVEL >= 3:
                output = event['data']['output']
                if isinstance(output, AIMessage):
                    if output.tool_calls:
                        for tool_call in output.tool_calls:
                            print(f"\033[38;5;220m\n[Tool Call]: {tool_call['name']}({tool_call['args']})\033[0m")
                    
                    reasoning = output.additional_kwargs.get("reasoning_content")
                    if reasoning:
                        print(f"\n\033[90m[Reasoning]: {reasoning}\033[0m\n")

            if LOG_LEVEL >= 2:
                print(f"\n\033[38;5;254m[Worker] Step Complete", flush=True)

    if LOG_LEVEL >= 2:
        print(f"\n\033[38;5;254m[Worker] Task Complete", flush=True)
        
async def worker_loop(agent):
    """
    The 'Nervous System' loop with Retry Logic and DLQ persistence.
    """
    if LOG_LEVEL >= 2:
        print("\033[92m[Worker] System online. Polling for tasks...\033[0m")
    
    # Ensure DLQ directory exists if enabled
    if DLQ_ENABLED and not os.path.exists(DLQ_DIR):
        os.makedirs(DLQ_DIR)

    while True:
        task = agent_queue.pop_task()
        if task:
            # Extract metadata
            task_data = task.get("data", task)
            task_id = task.get("id", "unknown") if isinstance(task, dict) else "cli-task"
            retries = task.get("retries", 0)

            try:
                # Pass the whole task_data instead of just the content string
                await process_task(agent, task_id, task_data)
            except Exception as e:
                print(f"\033[91m[Worker] Error Task {task_id} failed: {e}\033[0m")
                if LOG_LEVEL >= 4:
                    print(f"\033[90m{traceback.format_exc()}\033[0m")
                
                if retries < MAX_RETRIES:
                    # Exponential backoff: 30s, 60s, 120s...
                    delay = 30 * (2 ** retries)
                    print(f"\033[93m[Retry] Scheduling retry {retries + 1}/{MAX_RETRIES} in {delay}s...\033[0m")
                    
                    agent_queue.push_task(
                        task_data=task_data, 
                        delay_seconds=delay, 
                        retry_count=retries + 1
                    )
                else:
                    print(f"\033[91m[Critical] Task {task_id} exceeded MAX_RETRIES.\033[0m")
                    
                    if DLQ_ENABLED:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{DLQ_DIR}/{timestamp}_{task_id}.json"
                        
                        dlq_payload = {
                            "task_id": task_id,
                            "user_input": user_input,
                            "error": str(e),
                            "timestamp": timestamp,
                            "status": "failed_after_max_retries"
                        }
                        
                        try:
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(dlq_payload, f, indent=4)
                            print(f"\033[93m[DLQ] Task persisted to {filename} for manual recovery.\033[0m")
                        except Exception as write_err:
                            print(f"\033[91m[Error] Failed to write to DLQ: {write_err}\033[0m")
                    else:
                        print(f"\033[91m[Critical] Task {task_id} dropped (DLQ disabled).\033[0m")
        
        await asyncio.sleep(1)