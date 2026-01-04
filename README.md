# NBA CLI

NBA schedule tracker with automatic calendar integration. Get every game on your Google Calendar with automatic daily updates.

## Features

- Track any NBA team, conference, or division
- Generates ICS calendar files compatible with Google Calendar, Apple Calendar, Outlook
- Auto-updates daily via GitHub Actions
- No API key required (uses free NBA.com data)

## Quick Start (Subscribe via URL)

The easiest way to use this is to subscribe to the calendar URLs directly:

1. Go to [calendar.google.com](https://calendar.google.com)
2. Click the **+** next to "Other calendars"
3. Click **"From URL"**
4. Paste one of the calendar URLs below
5. Click **"Add calendar"**

Your calendar will automatically update every day with new games, scores, and playoff matchups.

### Available Calendars

Visit [t8s1n.github.io/nba-cli](https://t8s1n.github.io/nba-cli) to get calendar links for all 30 teams.

## Local Installation

If you want to run this locally:

```bash
# Clone the repo
git clone https://github.com/t8s1n/nba-cli.git
cd nba-cli

# Install
pip install -e .

# Track teams
nba-cli track Lakers
nba-cli track Celtics

# Generate calendars
nba-cli sync
```

## CLI Commands

```bash
nba-cli init              # Interactive setup
nba-cli teams             # List all 30 teams
nba-cli teams -c East     # Filter by conference
nba-cli teams -d Pacific  # Filter by division
nba-cli conferences       # Show conference/division structure
nba-cli track <team>      # Add team to tracking
nba-cli track East        # Track entire conference
nba-cli track Pacific     # Track entire division
nba-cli untrack <team>    # Remove from tracking
nba-cli status            # Show current configuration
nba-cli sync              # Fetch schedule, generate calendars
nba-cli schedule          # View upcoming games
```

## Fork Your Own

Want to track different teams with automatic updates?

1. Fork this repository
2. Go to Settings > Variables > Actions
3. Add variable `NBA_CLI_CONFIG`:
   ```json
   {"season": "2024-25", "tracked": {"teams": ["LAL", "BOS"], "conferences": [], "divisions": []}}
   ```
4. Enable GitHub Pages (Settings > Pages > Source: main, folder: /docs)
5. Run the workflow: Actions > "Sync NBA Schedule" > "Run workflow"

Your calendars will be available at:
`https://YOUR-USERNAME.github.io/nba-cli/nba_lal.ics`

## Configuration

Config file location: `~/.config/nba-cli/config.json`

Example:
```json
{
  "season": "2024-25",
  "tracked": {
    "teams": ["LAL", "BOS", "GSW"],
    "conferences": ["West"],
    "divisions": ["Pacific"]
  }
}
```

## Team Abbreviations

| East | | West | |
|------|------|------|------|
| ATL | Hawks | DAL | Mavericks |
| BOS | Celtics | DEN | Nuggets |
| BKN | Nets | GSW | Warriors |
| CHA | Hornets | HOU | Rockets |
| CHI | Bulls | LAC | Clippers |
| CLE | Cavaliers | LAL | Lakers |
| DET | Pistons | MEM | Grizzlies |
| IND | Pacers | MIN | Timberwolves |
| MIA | Heat | NOP | Pelicans |
| MIL | Bucks | OKC | Thunder |
| NYK | Knicks | PHX | Suns |
| ORL | Magic | POR | Trail Blazers |
| PHI | 76ers | SAC | Kings |
| TOR | Raptors | SAS | Spurs |
| WAS | Wizards | UTA | Jazz |

## License

MIT
