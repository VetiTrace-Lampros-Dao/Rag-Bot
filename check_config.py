"""VeriTrace Help Bot — Configuration Checker

Verifies that all required environment variables are present in .env
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "GEMINI_API_KEY",
    "DISCORD_WEBHOOK_URL",
    "SLACK_WEBHOOK_URL",
    "VERITRACE_API_BASE_URL",
]

def main():
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        print(f"config FAILED — missing: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    print("config OK")

if __name__ == "__main__":
    main()
