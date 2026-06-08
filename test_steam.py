import urllib.request
import json
url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=EB23869004B2FBDC8341ACBE7EBA2DE4&steamids=76561198450670719"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read())
    print(json.dumps(data, indent=2))
