import json
import datetime
import asyncio
from typing import Any, Dict, Optional
from redis import Redis
from src.runtime.discord import DiscordInterface

# Initialize Redis connection - in a full implementation, this would come from a Config class
redis_client = Redis(host='localhost', port=6379, db=0, decode_responses=True)

def schedule_task(task_name: str, payload: Dict[str, Any], delay_seconds: int = 0) -> str:
    """
    Schedules a task for future execution via the Redis queue.
    
    Args:
        task_name: The name of the skill or function to execute.
        payload: The arguments for the task.
        delay_seconds: Time to wait before execution.
    """
    task_id = f"task_{int(datetime.datetime.now().timestamp())}"
    task_data = {
        "id": task_id,
        "task": task_name,
        "payload": payload,
        "scheduled_at": datetime.datetime.now().isoformat(),
        "execute_at": (datetime.datetime.now() + datetime.timedelta(seconds=delay_seconds)).isoformat()
    }
    
    # Push to a sorted set for scheduled tasks or a list for immediate ones
    if delay_seconds > 0:
        # Use timestamp as score for the sorted set
        redis_client.zadd("scheduled_tasks", {json.dumps(task_data): datetime.datetime.now().timestamp() + delay_seconds})
    else:
        redis_client.lpush("immediate_tasks", json.dumps(task_data))
        
    return f"Task {task_id} scheduled successfully."

async def send_discord_notification(channel_id: int, message: str) -> str:
    """
    Sends a real-time notification/alert to a Discord channel. 
    Use this tool whenever you need to notify the user externally, 
    send an asynchronous update, a reply to Discord,
    or alert a human operator of a system event 
    without waiting for the user to prompt you in the chat.

    Args:
        message[str]: The text to send.
        channel_id[int]: The snowflake ID of the target channel. If omitted, uses the default system channel.
    """
    bot = DiscordInterface._instance
    if bot is None:
        return "Error: Discord interface is not initialized."

    # Fallback to the bot's default target channel if none provided
    target_id = channel_id or bot.target_channel_id
    
    if not target_id:
        return "Error: No target Discord channel ID provided or configured."

    try:
        await bot.send_message(target_id, message)
        return f"Notification successfully sent to channel {target_id}."
    except Exception as e:
        return f"Failed to send Discord notification: {str(e)}"
