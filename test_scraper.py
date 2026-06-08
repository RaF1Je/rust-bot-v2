import asyncio
import aiohttp

async def main():
    steam_id = "76561198450670719"
    url = f"https://www.battlemetrics.com/players?filter[search]={steam_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            print(f"Status: {resp.status}")
            html = await resp.text()
            if "No players found" in html or "We couldn't find any players" in html:
                print("HTML: No players found")
            else:
                print(f"HTML Snippet length: {len(html)}")
                print("Redirects:", resp.history)

asyncio.run(main())
