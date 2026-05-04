import argparse
import sys
from src.runtime.queue import agent_queue

class AgentCLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Agentic Core - Task Injector",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self._setup_args()

    def _setup_args(self):
        self.parser.add_argument(
            "task", 
            type=str, 
            help="The task/instruction to push to the agent queue"
        )
        self.parser.add_argument(
            "--delay", 
            type=int, 
            default=0, 
            help="Delay in seconds before the task is executed"
        )
        
    def run(self):
        args = self.parser.parse_args()
        
        try:
            result = agent_queue.push_task(args.task, args.delay)
            print(f"Successfully sent task to queue: '{args.task}'")
            if args.delay > 0:
                print(f"Scheduled for execution in {args.delay} seconds.")
        except Exception as e:
            print(f"Error pushing task to Redis: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    AgentCLI().run()