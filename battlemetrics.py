import aiohttp
import logging
import os

logger = logging.getLogger(__name__)

# Fetch API key from env
BM_API_KEY = os.getenv("BM_API_KEY")

headers = {
    "Authorization": f"Bearer {BM_API_KEY}" if BM_API_KEY else ""
}
# Only add if we have a key
if not headers["Authorization"]:
    headers.pop("Authorization", None)

async def search_player_by_steamid(steam_id: str):
    """
    Find player bm_id by searching their SteamID64
    """
    url = "https://api.battlemetrics.com/players/match"
    payload = {
        "data": [
            {
                "type": "identifier",
                "attributes": {
                    "type": "steamID",
                    "identifier": steam_id
                }
            }
        ]
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("data"):
                    # Return the first match's bm_id and name
                    player = data["data"][0]
                    return player.get("id"), player.get("attributes", {}).get("name", "Unknown")
            elif resp.status == 401:
                logger.error("BM_API_KEY is missing or invalid. Authentication required for /players/match.")
            else:
                logger.error(f"Failed to search player {steam_id}: {resp.status} {await resp.text()}")
    return None, None

async def get_player_status(bm_id: str):
    """
    Get player status including current server
    """
    url = f"https://api.battlemetrics.com/players/{bm_id}?include=server"
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                # Check included for server data
                is_online = False
                server_id = None
                server_name = None
                
                if "included" in data:
                    for item in data["included"]:
                        if item["type"] == "server":
                            is_online = True
                            server_id = item["attributes"]["id"]
                            server_name = item["attributes"]["name"]
                            break
                            
                return is_online, server_id, server_name
            else:
                logger.error(f"Failed to get player status for {bm_id}: {resp.status}")
    return False, None, None

async def get_server_info(bm_id: str):
    """
    Get server details (status, players, max players, name)
    """
    url = f"https://api.battlemetrics.com/servers/{bm_id}"
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                attrs = data["data"]["attributes"]
                return {
                    "name": attrs["name"],
                    "status": attrs["status"],
                    "players": attrs["players"],
                    "max_players": attrs["maxPlayers"]
                }
            else:
                logger.error(f"Failed to get server info for {bm_id}: {resp.status}")
    return None
