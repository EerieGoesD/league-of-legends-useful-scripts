import sys
import time
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

def build_url(allies, enemies, bans, rank_range="all"):
    params = [f"user-role=support", f"rank-range={rank_range}", "recommendation-method=classic"]
    for name, role in allies:
        params.append(f"ally={name}-{role}")
    for e in enemies:
        params.append(f"enemy={e}")
    for b in bans:
        params.append(f"ban={b}")
    return "https://loltheory.gg/lol/team-comp-analyzer/solo-queue?" + "&".join(params)

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
        src = driver.page_source
        print("--- PAGE SOURCE (first 3000 chars) ---")
        print(src[:3000])
        print("--- END ---")
        return "N/A"

OFFSETS = {
    "WITH you    [All]":    50.34,
    "WITHOUT you [All]":    50.34,
    "WITH you    [Silver]": 50.62,
    "WITHOUT you [Silver]": 50.62,
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

def ask_list(prompt):
    raw = input(prompt).strip()
    if not raw:
        return []
    return [x.strip().lower() for x in raw.split(',')]

def main():
    print("=== LOLTHEORY DEBUG SCRAPER ===\n")
    print("Enter 4 allies as: champ-role (e.g. nasus-top, talon-jungle)")
    print("Enter YOUR support pick separately.")
    print("Enter enemies as: champ (e.g. illaoi, shyvana)")
    print("Enter bans as: champ (e.g. aatrox, akali)")
    print("Leave blank to skip.\n")

    raw_allies = ask_list("Allies (comma separated, NO support): ")
    allies = []
    for a in raw_allies:
        parts = a.split('-')
        if len(parts) == 2:
            allies.append((parts[0], parts[1]))
        else:
            print(f"  WARNING: skipping '{a}' - expected format champ-role")

    my_pick = input("Your support pick (e.g. yuumi): ").strip().lower()

    enemies = ask_list("Enemies (comma separated): ")
    bans = ask_list("Bans (comma separated): ")

    allies_with_me = allies + [(my_pick, 'support')] if my_pick else allies
    allies_without_me = allies

    urls = [
        build_url(allies_with_me, enemies, bans, rank_range="all"),
        build_url(allies_without_me, enemies, bans, rank_range="all"),
        build_url(allies_with_me, enemies, bans, rank_range="silver"),
        build_url(allies_without_me, enemies, bans, rank_range="silver"),
    ]
    labels = [
        "WITH you    [All]",
        "WITHOUT you [All]",
        "WITH you    [Silver]",
        "WITHOUT you [Silver]",
    ]

    for label, url in zip(labels, urls):
        print(f"\n{label}:\n  {url}")

    print("\nStarting 4 Chrome instances (headless)...")
    drivers = [create_driver() for _ in range(4)]

    try:
        print("Scraping all 4 URLs in parallel...")
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(scrape_winrate, drivers, urls))

        print(f"\n{'='*80}")
        for label, wr in zip(labels, results):
            print(format_result(label, wr))
        print(f"{'='*80}")
    finally:
        for d in drivers:
            d.quit()

if __name__ == "__main__":
    main()
