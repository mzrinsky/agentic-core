import asyncio
import os
import signal
import argparse
from src.core.orchestrator import AgentFactory
from src.config.loader import ConfigLoader

# Initialize config for log level access
config = ConfigLoader()

async def main():
    """
    Main Entry Point for Agentic Core.
    Wires the Factory -> Agent -> Runtime Loop.
    """
    parser = argparse.ArgumentParser(description="Agentic Core Worker")
    parser.add_argument(
        "--log-level", 
        type=int, 
        choices=[0, 1, 2, 3, 4], 
        default=2, 
        help="Set the system log level (0: Errors, 1: Basic, 2: Verbose, 3: Debug, 4: Trace)"
    )
    parser.add_argument(
        "--no-manage-server", 
        action="store_true", 
        help="Disable automatic model loading/runtime management via ServerManager"
    )
    args, unknown = parser.parse_known_args()

    # Set the environment variable so that the Worker/ConfigLoader can find it
    # This maintains compatibility with the existing worker logic
    os.environ["AGENT_LOG_LEVEL"] = str(args.log_level)
    os.environ["MANAGE_SERVER"] = "false" if args.no_manage_server else "true"

    def handle_exit(sig, frame):
        if config.get_log_level() >= 2:
            print(f"\033[94m[System] Caught signal {sig}. Cleaning up...\033[0m", flush=True)
        # Assuming server_manager is available in the scope or imported
        from src.runtime.server_manager import server_manager
        server_manager.stop()
        os._exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    if config.get_log_level() >= 2:
        print("\033[94m[System] 🚀 Starting Agentic Core...\033[0m", flush=True)

    # pull imports that touch the queue / redis, or other external deps here, so we load fast for simple things like help.
    from src.tools.system_tools import schedule_task, send_discord_notification
    from src.runtime.worker import worker_loop
    from src.runtime.interface import start_discord_interface

    # Initialize the Discord Interface
    bot = await start_discord_interface()
    if bot:
        # Run the bot in the background
        asyncio.create_task(bot.start(os.getenv("DISCORD_BOT_TOKEN")))

    # Setup the Factory
    factory = AgentFactory(
        config_path="./config", 
        agent_root="./agent"
    )

    # Assemble the Agent
    # We inject the system tools here. Skills path is handled by the factory.
    agent, backend = await factory.build_agent(
        tools=[schedule_task, send_discord_notification],
        base_skills_path="./skills"
    )

    # Start the Worker Loop (Blocking)
    try:
        await worker_loop(agent)
    except asyncio.CancelledError:
        if config.get_log_level() >= 2:
            print("\n[System] Agentic Core Shutting down gracefully...", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass