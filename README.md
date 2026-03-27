# League of Legends Useful Scripts

Personal Python scripts I use for League of Legends.

### `items.py`
Tracks total item gold value for your team in real time during a live game using the [Live Client Data API](https://developer.riotgames.com/docs/lol#game-client-api_live-client-data-api). Pulls item prices from Data Dragon.

### `champ_select.py`
Reads champ select state from the LCU API (auto-detects the lockfile), builds a [loltheory.gg](https://loltheory.gg) team comp URL, and scrapes predicted winrates.

### `champ_select_debug.py`
Same as above but for debug purposes (more verbose).
