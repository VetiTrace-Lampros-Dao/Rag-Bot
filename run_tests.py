#!/usr/bin/env python3
"""
Test runner for VeriTrace Help Bot LangGraph Orchestrator.
Runs the 7 test cases specified in the spec and prints step-by-step trace of outputs.
"""

import os
import sys
import logging
import asyncio
import time

# Ensure project root in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from orchestrator.graph import run_turn, init_graph

async def main():
    print("=" * 60)
    print("  VERITRACE HELP BOT — PROGRAMMATIC VERIFICATION")
    print("=" * 60)
    
    # Initialize graph
    print("\nInitializing orchestrator graph...")
    await init_graph()
    print("Graph initialized successfully.")

    session_id = "test-session-verification-123"

    test_cases = [
        (
            "Test 1: RAG-only question",
            "How does the matching threshold work?"
        ),
        (
            "Test 2: Backend check tool",
            "Was file abc123flagged flagged as a duplicate?"
        ),
        (
            "Test 3: Notify tool",
            "Let the team know this one's flagged"
        ),
        (
            "Test 4: Follow-up referencing context",
            "What was the content ID of the duplicate file we found in that check?"
        ),
        (
            "Test 5: Multi-step chain (check -> matches -> notify)",
            "Check if file abc123flagged is a duplicate, and if it is, show me what it matches and let the team know."
        ),
        (
            "Test 6: Out of scope question",
            "What's VeriTrace's monthly subscription pricing?"
        ),
        (
            "Test 7: Backend unreachable fallback",
            "Was file hash_xyz_123 flagged as a duplicate?"
        )
    ]

    for i, (title, prompt) in enumerate(test_cases):
        print("\n" + "-" * 50)
        print(f"RUNNING: {title}")
        print(f"Prompt: {prompt}")
        print("-" * 50)
        print("Thinking...")
        
        try:
            # We run the synchronous run_turn since it wraps the execution loop
            result = run_turn(session_id, prompt)
            print(f"\nResponse:\n{result['reply']}")
        except Exception as e:
            print(f"\nExecution failed with error: {e}")
        
        # Stagger the calls to respect free tier rate limits (15 RPM)
        if i < len(test_cases) - 1:
            print("\nSleeping 5 seconds to avoid API rate limit...")
            time.sleep(5)

if __name__ == "__main__":
    # Run the async main
    asyncio.run(main())
