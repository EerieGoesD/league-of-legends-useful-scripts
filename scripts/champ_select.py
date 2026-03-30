import requests, urllib3, time, os, subprocess, re, sys
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

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

def get_champ_select(port, password, debug=False):
    url = f"https://127.0.0.1:{port}/lol-champ-select/v1/session"
    try:
        r = requests.get(url, auth=('riot', password), verify=False, timeout=5)
        if r.status_code == 200:
            return r.json()
        if debug:
            print(f"  [DEBUG] LCU status {r.status_code}: {r.text[:200]}")
        return None
    except Exception as e:
        if debug:
            print(f"  [DEBUG] LCU error: {e}")
        return None

def parse_session(session, champ_map, debug=False):
    ROLE_MAP = {'top': 'top', 'jungle': 'jungle', 'middle': 'middle',
                'bottom': 'bottom', 'utility': 'support'}
    my_cell = session.get('localPlayerCellId')

    allies, enemies, bans = [], [], []

    for p in session.get('myTeam', []):
        cid = p.get('championId', 0)
        pos = p.get('assignedPosition', '')
        if cid and cid in champ_map:
            allies.append({
                'name': champ_map[cid],
                'role': ROLE_MAP.get(pos, ''),
                'is_me': p.get('cellId') == my_cell
            })

    for p in session.get('theirTeam', []):
        cid = p.get('championId', 0)
        if cid and cid in champ_map:
            enemies.append(champ_map[cid])

    for action_group in session.get('actions', []):
        for action in action_group:
            if action.get('type') == 'ban' and action.get('completed'):
                cid = action.get('championId', 0)
                if cid and cid in champ_map:
                    bans.append(champ_map[cid])

    if debug:
        print(f"  [DEBUG] allies: {len(allies)}, enemies: {len(enemies)}, bans: {len(bans)}")
    return allies, enemies, bans

# ── Build loltheory URLs ──

def build_url(allies, enemies, bans, include_me=True, rank_range="all"):
    params = [f"user-role=support", f"rank-range={rank_range}", "recommendation-method=classic"]

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

# ── Scrape winrate with Selenium ──

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    return webdriver.Chrome(options=options)

def scrape_winrate(driver, url):
    driver.get(url)
    try:
        def winrate_loaded(d):
            els = d.find_elements(By.CSS_SELECTOR, ".champion-column.win-rate.font-number")
            for el in els:
                if '%' in el.text:
                    return el
            return False
        el = WebDriverWait(driver, 20).until(winrate_loaded)
        return el.text.strip()
    except:
        return "N/A"

# ── Offset / PLAY-DODGE logic ──

OFFSETS = {
    "WITH you    [All]":    55.52,
    "WITHOUT you [All]":    55.52,
    "WITH you    [Silver]": 54.34,
    "WITHOUT you [Silver]": 54.34,
}

def format_result(label, wr_str):
    offset = OFFSETS[label]
    median = (50.0 + offset) / 2.0
    try:
        wr = float(wr_str.replace('%', ''))
        verdict = "PLAY THIS GAME!" if wr >= median else "DODGE THIS GAME!"
        return f"  {label}: {wr_str} | Offset: {offset:.2f}% | Median: {median:.2f}% | {verdict}"
    except ValueError:
        return f"  {label}: {wr_str} | Offset: {offset:.2f}% | Median: {median:.2f}% | N/A"

# ── Main loop ──

def main():
    debug = '--debug' in sys.argv

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
    last_status = None
    fail_count = 0
    drivers = None
    in_champ_select = False
    print("Waiting for champ select...\n")

    try:
        while True:
            session = get_champ_select(port, password, debug)
            if session is None:
                if in_champ_select:
                    in_champ_select = False
                    last_status = None
                    last_comp = None
                    print("\nChamp select ended. Waiting for next champ select...\n")
                fail_count += 1
                if fail_count >= 5:
                    lockfile = find_lockfile()
                    if lockfile:
                        new_port, new_password = parse_lockfile(lockfile)
                        if new_port != port:
                            port, password = new_port, new_password
                            print(f"Reconnected to LCU on port {port}")
                    fail_count = 0
            else:
                fail_count = 0
            if session and 'myTeam' in session:
                in_champ_select = True
                allies, enemies, bans = parse_session(session, champ_map, debug)

                comp = str(sorted(a['name'] for a in allies)) + str(sorted(enemies))

                # Show live status while waiting for all picks
                if comp != last_comp and not (len(allies) == 5 and len(enemies) == 5):
                    status_key = f"{len(allies)}a-{len(enemies)}e-{len(bans)}b"
                    if status_key != last_status:
                        last_status = status_key
                        os.system("cls")
                        print("Champ Select - waiting for all picks...\n")
                        print(f"  Bans: {len(bans)}/10 completed" + (f" - {', '.join(bans)}" if bans else ""))
                        ally_str = ", ".join(f"{a['name']} ({a['role']})" for a in allies)
                        print(f"  Ally picks: {len(allies)}/5" + (f" - {ally_str}" if allies else ""))
                        print(f"  Enemy picks: {len(enemies)}/5" + (f" - {', '.join(enemies)}" if enemies else ""))
                        print()

                if comp != last_comp and len(allies) == 5 and len(enemies) == 5:
                    last_comp = comp
                    last_status = None

                    os.system("cls")
                    print("ALLIES:", ", ".join(f"{a['name']} ({a['role']})" for a in allies))
                    print("ENEMIES:", ", ".join(enemies))
                    print("BANS:", ", ".join(bans))
                    print("\nFetching winrates from loltheory.gg (4 threads)...\n")

                    if drivers is None:
                        drivers = [create_driver() for _ in range(4)]

                    urls = [
                        build_url(allies, enemies, bans, include_me=True, rank_range="all"),
                        build_url(allies, enemies, bans, include_me=False, rank_range="all"),
                        build_url(allies, enemies, bans, include_me=True, rank_range="silver"),
                        build_url(allies, enemies, bans, include_me=False, rank_range="silver"),
                    ]

                    labels = [
                        "WITH you    [All]",
                        "WITHOUT you [All]",
                        "WITH you    [Silver]",
                        "WITHOUT you [Silver]",
                    ]

                    print("URLs being scraped:")
                    for label, url in zip(labels, urls):
                        print(f"  {label}: {url}")
                    print()

                    with ThreadPoolExecutor(max_workers=4) as pool:
                        results = list(pool.map(scrape_winrate, drivers, urls))

                    os.system("cls")
                    print("ALLIES:", ", ".join(f"{a['name']} ({a['role']})" for a in allies))
                    print("ENEMIES:", ", ".join(enemies))
                    print()
                    for label, wr in zip(labels, results):
                        print(format_result(label, wr))
                    print("\nPolling for changes...")
            time.sleep(3)
    except KeyboardInterrupt:
        pass
    finally:
        if drivers:
            for d in drivers:
                d.quit()

if __name__ == "__main__":
    main()