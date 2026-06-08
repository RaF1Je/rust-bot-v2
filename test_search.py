import asyncio
import aiohttp

async def main():
    steam_id = "76561198450670719"
    urls = [
        f"https://api.battlemetrics.com/players?filter[match]={steam_id}",
        f"https://api.battlemetrics.com/players/match?identifier={steam_id}&type=steamID"
    ]
    async with aiohttp.ClientSession() as session:
        for url in urls:
            async with session.get(url) as resp:
                print(f"URL: {url} -> Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Results: {len(data.get('data', []))}")
                else:
                    print(await resp.text())

asyncio.run(main())
