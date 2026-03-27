import requests, urllib3, time, os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://127.0.0.1:2999/liveclientdata"

# Load item gold values from Data Dragon
def load_item_gold():
    versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
    data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{versions[0]}/data/en_US/item.json").json()["data"]
    return {int(k): v["gold"]["total"] for k, v in data.items()}

print("Loading item data from Data Dragon...")
item_gold = load_item_gold()
print(f"Loaded {len(item_gold)} items.")

while True:
    try:
        active = requests.get(f"{URL}/activeplayername", verify=False).json()
        players = requests.get(f"{URL}/playerlist", verify=False).json()

        my_team = next(p["team"] for p in players if p["summonerName"] == active)

        allies = []
        for p in players:
            if p["team"] == my_team:
                total = 0
                for item in p["items"]:
                    if item["slot"] == 6:  # skip trinket
                        continue
                    gold = item_gold.get(item["itemID"], 0)
                    total += gold * item.get("count", 1)
                allies.append((p["championName"], p["summonerName"], total))

        allies.sort(key=lambda x: x[2], reverse=True)

        os.system("cls")
        for champ, name, gold in allies:
            print(f"{gold:>6}g  {champ} ({name})")

        time.sleep(1)
    except (requests.ConnectionError, TypeError, StopIteration, KeyError):
        os.system("cls")
        print("Waiting for a live game...")
        time.sleep(5)