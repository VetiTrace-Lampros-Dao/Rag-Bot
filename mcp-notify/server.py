import os
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("veritrace-notify")

@mcp.tool()
def notify_discord(message: str) -> str:
    """Send a notification message to the Discord channel."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return "Discord notification failed: DISCORD_WEBHOOK_URL is not set."
    
    try:
        response = requests.post(webhook_url, json={"content": message})
        response.raise_for_status()
        return "Discord notification sent"
    except requests.exceptions.RequestException as e:
        return f"Discord notification failed: {str(e)}"

@mcp.tool()
def notify_slack(message: str) -> str:
    """Send a notification message to the Slack channel."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return "Slack notification failed: SLACK_WEBHOOK_URL is not set."
    
    try:
        response = requests.post(webhook_url, json={"text": message})
        response.raise_for_status()
        return "Slack notification sent"
    except requests.exceptions.RequestException as e:
        return f"Slack notification failed: {str(e)}"

if __name__ == "__main__":
    mcp.run()
