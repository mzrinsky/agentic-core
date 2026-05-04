import discord
import os
from src.runtime.discord import DiscordInterface
from src.config.loader import ConfigLoader

config = ConfigLoader()

async def start_discord_interface():
    """
    Initializes and runs the Discord bot interface.
    """
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if not discord_token:
        if config.get_log_level() > 0:
            print("\033[93m[Interface] No DISCORD_BOT_TOKEN found. Skipping Discord interface.")
        return None

    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.presences = True
    
    bot = DiscordInterface(intents=intents)
    return bot