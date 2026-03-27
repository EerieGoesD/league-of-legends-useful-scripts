import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def build_url(allies, enemies, bans):
    params = ["user-role=support", "rank-range=all", "recommendation-method=classic"]
    for name, role in allies:
        params.append(f"ally={name}-{role}")
    for e in enemies:
        params.append(f"enemy={e}")
    for b in bans:
        params.append(f"ban={b}")
    return "https://loltheory.gg/lol/team-comp-analyzer/solo-queue?" + "&".join(params)

def scrape_winrate(driver, url):
    print(f"\nURL: {url}\n")
    driver.get(url)
    try:
        def winrate_loaded(driver):
            els = driver.find_elements(By.CSS_SELECTOR, ".champion-column.win-rate.font-number")
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
            print(f"  WARNING: skipping '{a}' — expected format champ-role")

    my_pick = input("Your support pick (e.g. yuumi): ").strip().lower()

    enemies = ask_list("Enemies (comma separated): ")
    bans = ask_list("Bans (comma separated): ")

    allies_with_me = allies + [(my_pick, 'support')] if my_pick else allies
    allies_without_me = allies

    url_with = build_url(allies_with_me, enemies, bans)
    url_without = build_url(allies_without_me, enemies, bans)

    print("\n--- URL WITH support ---")
    print(url_with)
    print("\n--- URL WITHOUT support ---")
    print(url_without)

    print("\nStarting Chrome (headless)...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    driver = webdriver.Chrome(options=options)

    try:
        print("\n>>> Scraping WITH support...")
        wr_with = scrape_winrate(driver, url_with)
        print(f"Result: {wr_with}")

        print("\n>>> Scraping WITHOUT support...")
        wr_without = scrape_winrate(driver, url_without)
        print(f"Result: {wr_without}")

        print(f"\n{'='*30}")
        print(f"  WITH you:    {wr_with}")
        print(f"  WITHOUT you: {wr_without}")
        print(f"{'='*30}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()