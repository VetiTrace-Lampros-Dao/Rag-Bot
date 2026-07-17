#!/usr/bin/env python3
"""
VeriTrace Help Bot — CLI interface.

A thin interactive loop calling run_turn() for local testing.
Uses a fixed session_id so conversation history persists across turns.
"""

import sys
import os
import logging

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_project_root, ".env"))


def main():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print("=" * 60)
    print("  VeriTrace Help Bot — CLI")
    print("  Type your question, or 'quit' / 'exit' to leave.")
    print("=" * 60)
    print()

    from orchestrator.graph import run_turn

    session_id = "cli-session-local"

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print("Thinking...")
        try:
            result = run_turn(session_id, user_input)
            print(f"\nBot: {result['reply']}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
