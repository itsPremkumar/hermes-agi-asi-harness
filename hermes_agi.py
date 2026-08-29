#!/usr/bin/env python3
"""
Hermes AGI/ASI Harness — Main Entry Point

Usage:
    python hermes_agi.py                  # Start interactive mode
    python hermes_agi.py --goal "..."     # Execute a goal
    python hermes_agi.py --zero-cost      # Free-first mode
    python hermes_agi.py --offline        # Offline mode
    python hermes_agi.py --health         # Health check
    python hermes_agi.py --list-plugins   # List all plugins
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.runtime.kernel import HermesKernel, KernelConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("hermes_agi")


async def main():
    parser = argparse.ArgumentParser(description="Hermes AGI/ASI Harness")
    parser.add_argument("--goal", type=str, help="Goal to execute")
    parser.add_argument("--zero-cost", action="store_true", help="Free-first mode")
    parser.add_argument("--offline", action="store_true", help="Offline mode")
    parser.add_argument("--health", action="store_true", help="Health check")
    parser.add_argument("--list-plugins", action="store_true", help="List plugins")
    parser.add_argument("--profile", type=str, default="default", help="Profile name")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create kernel config
    config = KernelConfig(
        profile=args.profile,
        zero_cost=args.zero_cost,
        offline=args.offline,
    )
    
    # Create kernel
    kernel = HermesKernel(config=config)
    
    try:
        # Boot kernel
        await kernel.boot()
        
        if args.health:
            health = await kernel.health_check()
            print("\n🏥 Health Check:")
            for key, value in health.items():
                print(f"  {key}: {value}")
            return
        
        if args.list_plugins:
            if kernel.plugin_manager:
                plugins = kernel.plugin_manager.list_plugins()
                print("\n🔌 Plugins:")
                for p in plugins:
                    print(f"  {p['name']}: {'✅' if p['enabled'] else '❌'} {p.get('capabilities', [])}")
            return
        
        if args.goal:
            from core.runtime.kernel import Task
            task = Task(goal=args.goal)
            task_id = await kernel.submit_task(task)
            print(f"\n🚀 Task submitted: {task_id}")
            print(f"   Goal: {args.goal}")
            return
        
        # Interactive mode
        print("""
╔═══════════════════════════════════════════════════════════════╗
║           HERMES AGI/ASI HARNESS v2.0 ULTIMATE               ║
║                                                               ║
║  Free-first, modular, model-agnostic agent harness           ║
║  Type 'help' for commands, 'quit' to exit                    ║
╚═══════════════════════════════════════════════════════════════╝
        """)
        
        while True:
            try:
                user_input = input("\n🎯 Goal> ").strip()
                
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "q"):
                    break
                if user_input.lower() == "help":
                    print("\nCommands:")
                    print("  health     - Health check")
                    print("  plugins    - List plugins")
                    print("  models     - List models")
                    print("  <goal>     - Execute a goal")
                    print("  quit       - Exit")
                    continue
                if user_input.lower() == "health":
                    health = await kernel.health_check()
                    for key, value in health.items():
                        print(f"  {key}: {value}")
                    continue
                if user_input.lower() == "plugins":
                    if kernel.plugin_manager:
                        for p in kernel.plugin_manager.list_plugins():
                            print(f"  {p['name']}: {'✅' if p['enabled'] else '❌'}")
                    continue
                if user_input.lower() == "models":
                    if kernel.model_router:
                        for m in kernel.model_router.list_models():
                            print(f"  {m.name} ({m.provider}) - {m.cost}")
                    continue
                
                # Execute goal
                from core.runtime.kernel import Task
                task = Task(goal=user_input)
                task_id = await kernel.submit_task(task)
                print(f"Task submitted: {task_id}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    finally:
        await kernel.shutdown()
        print("\n👋 Hermes AGI/ASI Harness shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
