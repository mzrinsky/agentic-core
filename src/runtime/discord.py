import discord
import os
from src.runtime.queue import agent_queue

class DiscordInterface(discord.Client):
    _instance = None  # Singleton reference

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        DiscordInterface._instance = self
        self.target_channel_id = None # Set this via env or config

    async def on_ready(self):
        print(f"\033[94m[Discord] Logged in as {self.user} (ID: {self.user.id})\033[0m")
        # Optional: Auto-set target channel to the first one the bot has access to
        if not self.target_channel_id:
            bot_name_lower = self.user.name.lower()
            for guild in self.guilds:
                for channel in guild.text_channels:
                    if bot_name_lower in channel.name.lower():
                        self.target_channel_id = channel.id
                        print(f"[Discord] Target channel set to: {channel.name}")
                        break

    async def on_message(self, message):
        # Don't respond to self
        if message.author == self.user:
            return

        # Only listen to specific channel or DMs
        if self.target_channel_id and message.channel.id != self.target_channel_id:
            return

        print(f"\033[32m[Discord Input] {message.author}: {message.content}\033[0m")
        
        # Push a clean dictionary to the queue
        agent_queue.push_task({
            "instruction": f"You received a Discord notification from {message.author.name}. Please process it and notify via Discord.",
            "content": message.content,
            "channel_id": message.channel.id,
            "user_id": message.author.id,
            "type": "discord-message"
        })

    async def send_message(self, channel_id: int, content: str):
        print(f"[Discord_Bot] Attemping to send message to '{channel_id}'")
        channel = self.get_channel(channel_id)

        if channel is None:
            try:
                # Use fetch_channel to get the channel object from the API
                channel = await self.fetch_channel(channel_id)
            except discord.NotFound:
                raise Exception(f"Channel {channel_id} was not found on Discord.")
            except discord.Forbidden:
                raise Exception(f"I do not have permission to send messages to channel {channel_id}.")
            except discord.HTTPException as e:
                raise Exception(f"Discord API error occurred while fetching channel {channel_id}: {e}")

        if channel:
            await channel.send(content)
        else:
            # This part is technically redundant if the try/except block above 
            # raises everything, but kept for absolute safety.
            raise Exception(f"Could not resolve Discord channel {channel_id}")