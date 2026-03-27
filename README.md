# League of Legends Useful Scripts

Personal Python scripts I use for League of Legends.

## Scripts

### `items.py`
Tracks total item gold value for your team in real time during a live game using the [Live Client Data API](https://developer.riotgames.com/docs/lol#game-client-api_live-client-data-api). Pulls item prices from Data Dragon so values are always up to date.

### `champ_select.py`
Reads champ select state from the LCU API (auto-detects the lockfile), builds a [loltheory.gg](https://loltheory.gg) team comp URL, and scrapes predicted winrates - both with and without your pick. Polls for changes throughout champ select.

### `champ_select_debug.py`
Manual/debug version of the champ select script. You enter allies, enemies, and bans by hand, and it scrapes loltheory.gg via headless Chrome (Selenium).

## Requirements

- Python 3
- `requests`
- `selenium` + ChromeDriver (only for `champ_select_debug.py`)
- League of Legends client running (for `items.py` and `champ_select.py`)
