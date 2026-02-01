"""NBA API client for fetching schedule data."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests

from .config import NBA_TEAMS

logger = logging.getLogger(__name__)


@dataclass
class Game:
    """Represents an NBA game."""
    game_id: str
    game_date: datetime
    home_team_id: int
    home_team: str
    home_team_name: str
    away_team_id: int
    away_team: str
    away_team_name: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    arena: Optional[str] = None
    arena_city: Optional[str] = None
    arena_state: Optional[str] = None
    completed: bool = False
    season: str = ""
    season_type: str = "Regular Season"
    
    @property
    def matchup(self) -> str:
        return f"{self.away_team} @ {self.home_team}"
    
    @property
    def matchup_full(self) -> str:
        return f"{self.away_team_name} @ {self.home_team_name}"
    
    def involves_team(self, team_abbrev: str) -> bool:
        abbrev = team_abbrev.upper()
        return self.home_team == abbrev or self.away_team == abbrev
    
    def involves_team_id(self, team_id: int) -> bool:
        return self.home_team_id == team_id or self.away_team_id == team_id
    
    @property
    def location(self) -> str:
        parts = []
        if self.arena:
            parts.append(self.arena)
        if self.arena_city:
            city_state = self.arena_city
            if self.arena_state:
                city_state += f", {self.arena_state}"
            parts.append(city_state)
        return ", ".join(parts) if parts else ""


class NBAClient:
    """Client for fetching NBA schedule data."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.nba.com/",
        })
    
    def get_full_schedule(self, season_year: int) -> list[Game]:
        url = f"https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/{season_year}/league/00_full_schedule.json"
        logger.info(f"Fetching full schedule from {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to fetch schedule: {e}")
            return []
        
        games = []
        season_str = f"{season_year}-{str(season_year + 1)[2:]}"
        
        for month_data in data.get("lscd", []):
            month_schedule = month_data.get("mscd", {})
            for game_data in month_schedule.get("g", []):
                game = self._parse_game(game_data, season_str)
                if game:
                    games.append(game)
        
        logger.info(f"Found {len(games)} total games")
        return games
    
    def _parse_game(self, game_data: dict, season: str) -> Optional[Game]:
        try:
            game_id = game_data.get("gid", "")
            game_date_str = game_data.get("gdte", "")
            game_time_str = game_data.get("etm", "")
            
            if game_time_str:
                try:
                    game_date = datetime.strptime(game_time_str, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    game_date = datetime.strptime(game_date_str, "%Y-%m-%d").replace(hour=19, minute=30)
            else:
                game_date = datetime.strptime(game_date_str, "%Y-%m-%d").replace(hour=19, minute=30)
            
            visitor = game_data.get("v", {})
            away_team_id = visitor.get("tid", 0)
            away_abbrev = visitor.get("ta", "")
            away_name = visitor.get("tn", "")
            away_city = visitor.get("tc", "")
            away_score = visitor.get("s")
            away_score = int(away_score) if away_score and away_score != "" else None
            
            home = game_data.get("h", {})
            home_team_id = home.get("tid", 0)
            home_abbrev = home.get("ta", "")
            home_name = home.get("tn", "")
            home_city = home.get("tc", "")
            home_score = home.get("s")
            home_score = int(home_score) if home_score and home_score != "" else None
            
            arena = game_data.get("an", "")
            arena_city = game_data.get("ac", "")
            arena_state = game_data.get("as", "")
            
            status = game_data.get("st", 1)
            completed = status == 3
            
            seri = game_data.get("seri", "")
            if "Playoff" in seri or "Finals" in seri:
                season_type = "Playoffs"
            elif "Play-In" in seri:
                season_type = "Play-In"
            else:
                season_type = "Regular Season"
            
            return Game(
                game_id=str(game_id),
                game_date=game_date,
                home_team_id=home_team_id,
                home_team=home_abbrev,
                home_team_name=f"{home_city} {home_name}",
                away_team_id=away_team_id,
                away_team=away_abbrev,
                away_team_name=f"{away_city} {away_name}",
                home_score=home_score,
                away_score=away_score,
                arena=arena,
                arena_city=arena_city,
                arena_state=arena_state,
                completed=completed,
                season=season,
                season_type=season_type,
            )
        except Exception as e:
            logger.warning(f"Error parsing game: {e}")
            return None
    
    def get_full_season_schedule(
        self,
        season: str,
        team_ids: Optional[list[int]] = None,
        include_preseason: bool = False,
        include_playoffs: bool = True,
    ) -> list[Game]:
        season_year = int(season.split("-")[0])
        all_games = self.get_full_schedule(season_year)
        
        if team_ids:
            filtered = []
            seen = set()
            for g in all_games:
                if g.game_id in seen:
                    continue
                for team_id in team_ids:
                    if g.involves_team_id(team_id):
                        seen.add(g.game_id)
                        filtered.append(g)
                        break
            all_games = filtered
        
        all_games.sort(key=lambda g: g.game_date)
        logger.info(f"Returning {len(all_games)} games")
        return all_games
