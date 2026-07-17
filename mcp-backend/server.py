import os
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("veritrace-backend")

def get_base_url() -> str:
    return os.environ.get("VERITRACE_API_BASE_URL", "http://localhost:8080").rstrip("/")

@mcp.tool()
def check_duplicate(sha256_hash: str) -> str:
    """Check if an exact duplicate exists using its SHA-256 hash."""
    base_url = get_base_url()
    try:
        response = requests.get(f"{base_url}/api/v1/fingerprint/{sha256_hash}")
        if response.status_code == 200:
            return f"Match found! Fingerprint: {response.json()}"
        elif response.status_code == 404:
            return "No exact match found."
        else:
            return f"Error connecting to backend API: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to VeriTrace backend: {str(e)}"

@mcp.tool()
def get_verification_status(asset_id: str) -> str:
    """Get the verification status and confidence score of an asset by its ID."""
    base_url = get_base_url()
    try:
        response = requests.get(f"{base_url}/api/v1/assets/{asset_id}/verify")
        if response.status_code == 200:
            data = response.json()
            return f"Status: {data.get('status', 'Unknown')}, Confidence: {data.get('confidence', 'N/A')}"
        elif response.status_code == 404:
            return "Asset not found."
        else:
            return f"Error connecting to backend API: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to VeriTrace backend: {str(e)}"

@mcp.tool()
def get_similar_matches(phash: str, threshold: int = 40) -> str:
    """Find visually similar matches using a perceptual hash and a Hamming distance threshold."""
    base_url = get_base_url()
    try:
        response = requests.get(
            f"{base_url}/api/v1/fingerprint/similar",
            params={"phash": phash, "threshold": threshold}
        )
        if response.status_code == 200:
            return f"Similar matches: {response.json()}"
        elif response.status_code == 404:
            return "No similar matches found within threshold."
        else:
            return f"Error connecting to backend API: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to VeriTrace backend: {str(e)}"

if __name__ == "__main__":
    # In standard execution, run the stdio server
    mcp.run()
