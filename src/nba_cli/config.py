"""Configuration management for NBA CLI."""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# NBA Teams with full info
NBA_TEAMS = {
    # Eastern Conference - Atlantic
    "BOS": {"name": "Boston Celtics", "full_name": "Boston Celtics", "conference": "East", "division": "Atlantic", "id": 1610612738},
    "BKN": {"name": "Brooklyn Nets", "full_name": "Brooklyn Nets", "conference": "East", "division": "Atlantic", "id": 1610612751},
    "NYK": {"name": "New York Knicks", "full_name": "New York Knicks", "conference": "East", "division": "Atlantic", "id": 1610612752},
    "PHI": {"name": "Philadelphia 76ers", "full_name": "Philadelphia 76ers", "conference": "East", "division": "Atlantic", "id": 1610612755},
    "TOR": {"name": "Toronto Raptors", "full_name": "Toronto Raptors", "conference": "East", "division": "Atlantic", "id": 1610612761},
    # Eastern Conference - Central
    "CHI": {"name": "Chicago Bulls", "full_name": "Chicago Bulls", "conference": "East", "division": "Central", "id": 1610612741},
    "CLE": {"name": "Cleveland Cavaliers", "full_name": "Cleveland Cavaliers", "conference": "East", "division": "Central", "id": 1610612739},
    "DET": {"name": "Detroit Pistons", "full_name": "Detroit Pistons", "conference": "East", "division": "Central", "id": 1610612765},
    "IND": {"name": "Indiana Pacers", "full_name": "Indiana Pacers", "conference": "East", "division": "Central", "id": 1610612754},
    "MIL": {"name": "Milwaukee Bucks", "full_name": "Milwaukee Bucks", "conference": "East", "division": "Central", "id": 1610612749},
    # Eastern Conference - Southeast
    "ATL": {"name": "Atlanta Hawks", "full_name": "Atlanta Hawks", "conference": "East", "division": "Southeast", "id": 1610612737},
    "CHA": {"name": "Charlotte Hornets", "full_name": "Charlotte Hornets", "conference": "East", "division": "Southeast", "id": 1610612766},
    "MIA": {"name": "Miami Heat", "full_name": "Miami Heat", "conference": "East", "division": "Southeast", "id": 1610612748},
    "ORL": {"name": "Orlando Magic", "full_name": "Orlando Magic", "conference": "East", "division": "Southeast", "id": 1610612753},
    "WAS": {"name": "Washington Wizards", "full_name": "Washington Wizards", "conference": "East", "division": "Southeast", "id": 1610612764},
    # Western Conference - Northwest
    "DEN": {"name": "Denver Nuggets", "full_name": "Denver Nuggets", "conference": "West", "division": "Northwest", "id": 1610612743},
    "MIN": {"name": "Minnesota Timberwolves", "full_name": "Minnesota Timberwolves", "conference": "West", "division": "Northwest", "id": 1610612750},
    "OKC": {"name": "Oklahoma City Thunder", "full_name": "Oklahoma City Thunder", "conference": "West", "division": "Northwest", "id": 1610612760},
    "POR": {"name": "Portland Trail Blazers", "full_name": "Portland Trail Blazers", "conference": "West", "division": "Northwest", "id": 1610612757},
    "UTA": {"name": "Utah Jazz", "full_name": "Utah Jazz", "conference": "West", "division": "Northwest", "id": 1610612762},
    # Western Conference - Pacific
    "GSW": {"name": "Golden State Warriors", "full_name": "Golden State Warriors", "conference": "West", "division": "Pacific", "id": 1610612744},
    "LAC": {"name": "Los Angeles Clippers", "full_name": "Los Angeles Clippers", "conference": "West", "division": "Pacific", "id": 1610612746},
    "LAL": {"name": "Los Angeles Lakers", "full_name": "Los Angeles Lakers", "conference": "West", "division": "Pacific", "id": 1610612747},
    "PHX": {"name": "Phoenix Suns", "full_name": "Phoenix Suns", "conference": "West", "division": "Pacific", "id": 1610612756},
    "SAC": {"name": "Sacramento Kings", "full_name": "Sacramento Kings", "conference": "West", "division": "Pacific", "id": 1610612758},
    # Western Conference - Southwest
    "DAL": {"name": "Dallas Mavericks", "full_name": "Dallas Mavericks", "conference": "West", "division": "Southwest", "id": 1610612742},
    "HOU": {"name": "Houston Rockets", "full_name": "Houston Rockets", "conference": "West", "division": "Southwest", "id": 1610612745},
    "MEM": {"name": "Memphis Grizzlies", "full_name": "Memphis Grizzlies", "conference": "West", "division": "Southwest", "id": 1610612763},
    "NOP": {"name": "New Orleans Pelicans", "full_name": "New Orleans Pelicans", "conference": "West", "division": "Southwest", "id": 1610612740},
    "SAS": {"name": "San Antonio Spurs", "full_name": "San Antonio Spurs", "conference": "West", "division": "Southwest", "id": 1610612759},
}

NBA_CONFERENCES = ["East", "West"]

NBA_DIVISIONS = {
    "East": ["Atlantic", "Central", "Southeast"],
    "West": ["Northwest", "Pacific", "Southwest"],
}


def get_team_by_abbrev(abbrev: str) -> Optional[dict]:
    """Get team info by abbreviation."""
    return NBA_TEAMS.get(abbrev.upper())


def get_team_by_name(name: str) -> Optional[tuple[str, dict]]:
    """Get team info by name (partial match)."""
    name_lower = name.lower()
    for abbrev, info in NBA_TEAMS.items():
        if (name_lower in info["name"].lower() or 
            name_lower in info["full_name"].lower() or
            name_lower == abbrev.lower()):
            return abbrev, info
    return None


def get_teams_by_conference(conference: str) -> list[tuple[str, dict]]:
    """Get all teams in a conference."""
    conf = conference.capitalize()
    return [(abbrev, info) for abbrev, info in NBA_TEAMS.items() 
            if info["conference"] == conf]


def get_teams_by_division(division: str) -> list[tuple[str, dict]]:
    """Get all teams in a division."""
    div = division.capitalize()
    return [(abbrev, info) for abbrev, info in NBA_TEAMS.items() 
            if info["division"] == div]


class TrackedTeams(BaseModel):
    """Teams being tracked."""
    teams: list[str] = []  # Team abbreviations
    conferences: list[str] = []  # East, West
    divisions: list[str] = []  # Atlantic, Central, etc.
    
    def is_empty(self) -> bool:
        return not self.teams and not self.conferences and not self.divisions
    
    def get_all_team_ids(self) -> list[int]:
        """Get all team IDs based on tracked teams, conferences, and divisions."""
        team_ids = set()
        
        # Add directly tracked teams
        for abbrev in self.teams:
            team = get_team_by_abbrev(abbrev)
            if team:
                team_ids.add(team["id"])
        
        # Add teams from tracked conferences
        for conf in self.conferences:
            for abbrev, info in get_teams_by_conference(conf):
                team_ids.add(info["id"])
        
        # Add teams from tracked divisions
        for div in self.divisions:
            for abbrev, info in get_teams_by_division(div):
                team_ids.add(info["id"])
        
        return list(team_ids)


class Config(BaseModel):
    """Application configuration."""
    season: str = ""  # e.g., "2024-25"
    tracked: TrackedTeams = TrackedTeams()
    
    @classmethod
    def get_current_season(cls) -> str:
        """Get the current NBA season string."""
        now = datetime.now()
        # NBA season starts in October
        if now.month >= 10:
            return f"{now.year}-{str(now.year + 1)[2:]}"
        else:
            return f"{now.year - 1}-{str(now.year)[2:]}"


def get_config_dir() -> Path:
    """Get configuration directory."""
    if os.environ.get("NBA_CLI_CONFIG"):
        return Path(os.environ["NBA_CLI_CONFIG"]).parent
    
    config_home = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(config_home) / "nba-cli"


def get_config_path() -> Path:
    """Get configuration file path."""
    return get_config_dir() / "config.json"


def get_data_dir() -> Path:
    """Get data directory for calendars."""
    data_home = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(data_home) / "nba-cli"


def get_calendars_dir() -> Path:
    """Get calendars output directory."""
    return get_data_dir() / "calendars"


def load_config() -> Config:
    """Load configuration from file or environment."""
    # Check for environment variable (for CI/CD)
    if os.environ.get("NBA_CLI_CONFIG"):
        try:
            data = json.loads(os.environ["NBA_CLI_CONFIG"])
            return Config(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse NBA_CLI_CONFIG: {e}")
    
    # Load from file
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
            return Config(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
    
    # Return default config
    return Config(season=Config.get_current_season())


def save_config(config: Config) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config.model_dump(), f, indent=2)
    
    logger.info(f"Saved config to {config_path}")
