import requests, urllib3, time, os, subprocess, re, sys

urllib3.disable_warnings()

# ── Find lockfile via LeagueClientUx process ──

def find_lockfile():
    for drive in ['C', 'D', 'E']:
        path = f"{drive}:\\Riot Games\\League of Legends\\lockfile"
        if os.path.exists(path):
            return path
    try:
        result = subprocess.run(
            'wmic PROCESS WHERE "name=\'LeagueClientUx.exe\'" GET CommandLine',
            capture_output=True, text=True, shell=True
        )
        match = re.search(r'--install-directory=(.*?)"?\s', result.stdout)
        if match:
            p = os.path.join(match.group(1).strip('"'), 'lockfile')
            if os.path.exists(p):
                return p
    except:
        pass
    return None

def parse_lockfile(path):
    with open(path, 'r') as f:
        parts = f.read().strip().split(':')
    return parts[2], parts[3]  # port, password

# ── Champion ID → name map from Data Dragon ──

def load_champion_map():
    versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
    url = f"https://ddragon.leagueoflegends.com/cdn/{versions[0]}/data/en_US/champion.json"
    data = requests.get(url).json()['data']
    return {int(info['key']): info['id'].lower() for info in data.values()}

# ── Read champ select from LCU ──

def get_champ_select(port, password):
    url = f"https://127.0.0.1:{port}/lol-champ-select/v1/session"
    try:
        r = requests.get(url, auth=('riot', password), verify=False, timeout=5)
        print(f"  [DEBUG] LCU status: {r.status_code}")
        if r.status_code == 200:
            return r.json()
        else:
            print(f"  [DEBUG] Response: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"  [DEBUG] LCU error: {e}")
        return None

def parse_session(session, champ_map):
    ROLE_MAP = {'top': 'top', 'jungle': 'jungle', 'middle': 'middle',
                'bottom': 'bottom', 'utility': 'support'}
    my_cell = session.get('localPlayerCellId')

    allies, enemies, bans = [], [], []

    print(f"  [DEBUG] localPlayerCellId: {my_cell}")
    print(f"  [DEBUG] myTeam count: {len(session.get('myTeam', []))}")
    print(f"  [DEBUG] theirTeam count: {len(session.get('theirTeam', []))}")

    for p in session.get('myTeam', []):
        cid = p.get('championId', 0)
        pos = p.get('assignedPosition', '')
        print(f"  [DEBUG] ally: champId={cid}, position={pos}, cellId={p.get('cellId')}")
        if cid and cid in champ_map:
            allies.append({
                'name': champ_map[cid],
                'role': ROLE_MAP.get(pos, ''),
                'is_me': p.get('cellId') == my_cell
            })

    for p in session.get('theirTeam', []):
        cid = p.get('championId', 0)
        print(f"  [DEBUG] enemy: champId={cid}")
        if cid and cid in champ_map:
            enemies.append(champ_map[cid])

    for action_group in session.get('actions', []):
        for action in action_group:
            if action.get('type') == 'ban' and action.get('completed'):
                cid = action.get('championId', 0)
                if cid and cid in champ_map:
                    bans.append(champ_map[cid])

    print(f"  [DEBUG] parsed: {len(allies)} allies, {len(enemies)} enemies, {len(bans)} bans")
    return allies, enemies, bans

# ── Build loltheory URLs ──

def build_url(allies, enemies, bans, include_me=True):
    params = ["user-role=support", "rank-range=all", "recommendation-method=classic"]

    for a in allies:
        if not include_me and a['is_me']:
            continue
        if a['role']:
            params.append(f"ally={a['name']}-{a['role']}")

    for e in enemies:
        params.append(f"enemy={e}")

    for b in bans:
        params.append(f"ban={b}")

    return "https://loltheory.gg/lol/team-comp-analyzer/solo-queue?" + "&".join(params)

# ── Scrape winrate with requests ──

def scrape_winrate(url):
    try:
        r = requests.get(url, timeout=15)
        match = re.search(r'class="champion-column win-rate font-number"[^>]*>([0-9.]+%)', r.text)
        return match.group(1) if match else "N/A"
    except:
        return "N/A"

# ── Main loop ──

def main():
    print("Loading champion data from Data Dragon...")
    champ_map = load_champion_map()
    print(f"Loaded {len(champ_map)} champions.")

    print("Looking for League client lockfile...")
    lockfile = find_lockfile()
    if not lockfile:
        print("ERROR: Could not find lockfile. Is the League client running?")
        input("Press Enter to exit...")
        return

    port, password = parse_lockfile(lockfile)
    print(f"Connected to LCU on port {port}")

    last_comp = None
    print("Waiting for champ select...\n")

    try:
        while True:
            session = get_champ_select(port, password)
            if session and 'myTeam' in session:
                allies, enemies, bans = parse_session(session, champ_map)

                comp = str(sorted(a['name'] for a in allies)) + str(sorted(enemies))

                if comp != last_comp and len(allies) >= 4 and len(enemies) == 5:
                    last_comp = comp

                    os.system("cls")
                    print("ALLIES:", ", ".join(f"{a['name']} ({a['role']})" for a in allies))
                    print("ENEMIES:", ", ".join(enemies))
                    print("BANS:", ", ".join(bans))
                    print("\nFetching winrates from loltheory.gg...")

                    url_with = build_url(allies, enemies, bans, include_me=True)
                    url_without = build_url(allies, enemies, bans, include_me=False)

                    print(f"\nURL WITH:    {url_with}")
                    print(f"URL WITHOUT: {url_without}")

                    wr_with = scrape_winrate(url_with)
                    wr_without = scrape_winrate(url_without)

                    os.system("cls")
                    print("ALLIES:", ", ".join(f"{a['name']} ({a['role']})" for a in allies))
                    print("ENEMIES:", ", ".join(enemies))
                    print(f"\nURL WITH:    {url_with}")
                    print(f"URL WITHOUT: {url_without}")
                    print(f"\n  WITH you:    {wr_with}")
                    print(f"  WITHOUT you: {wr_without}")
                    print("\nPolling for changes...")
            time.sleep(3)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()