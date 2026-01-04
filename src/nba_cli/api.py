"""NBA API client for fetching schedule data."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder, scoreboardv2
from nba_api.stats.static import teams as nba_teams_static

from .config import NBA_TEAMS, get_team_by_abbrev

logger = logging.getLogger(__name__)


@dataclass
class Game:
    """Represents an NBA game."""
    game_id: str
    game_date: datetime
    home_team_id: int
    home_team: str  # abbreviation
    home_team_name: str
    away_team_id: int
    away_team: str  # abbreviation
    away_team_name: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    arena: Optional[str] = None
    completed: bool = False
    season: str = ""
    season_type: str = "Regular Season"  # Regular Season, Playoffs, Pre Season, etc.
    
    @property
    def matchup(self) -> str:
        """Get formatted matchup string."""
        return f"{self.away_team} @ {self.home_team}"
    
    @property
    def matchup_full(self) -> str:
        """Get full matchup string."""
        return f"{self.away_team_name} @ {self.home_team_name}"
    
    def involves_team(self, team_abbrev: str) -> bool:
        """Check if a team is playing in this game."""
        abbrev = team_abbrev.upper()
        return self.home_team == abbrev or self.away_team == abbrev
    
    def involves_team_id(self, team_id: int) -> bool:
        """Check if a team ID is playing in this game."""
        return self.home_team_id == team_id or self.away_team_id == team_id
    
    @property
    def score_display(self) -> str:
        """Get score display string."""
        if self.completed and self.home_score is not None and self.away_score is not None:
            return f"{self.away_team} {self.away_score} - {self.home_score} {self.home_team}"
        return ""


def get_team_abbrev_from_id(team_id: int) -> str:
    """Get team abbreviation from team ID."""
    for abbrev, info in NBA_TEAMS.items():
        if info["id"] == team_id:
            return abbrev
    return "UNK"


def get_team_name_from_id(team_id: int) -> str:
    """Get team name from team ID."""
    for abbrev, info in NBA_TEAMS.items():
        if info["id"] == team_id:
            return info["name"]
    return "Unknown"


class NBAClient:
    """Client for fetching NBA schedule data."""
    
    def __init__(self):
        self.request_delay = 0.6  # Delay between API requests to avoid rate limiting
    
    def _delay(self):
        """Add delay between requests."""
        time.sleep(self.request_delay)
    
    def get_season_games(
        self,
        season: str,
        team_ids: Optional[list[int]] = None,
        season_type: str = "Regular Season",
    ) -> list[Game]:
        """
        Get all games for a season.
        
        Args:
            season: Season string (e.g., "2024-25")
            team_ids: Optional list of team IDs to filter
            season_type: "Regular Season", "Playoffs", "Pre Season", "All Star"
        """
        games = []
        seen_game_ids = set()
        
        # Convert season format for API (2024-25 -> 2024)
        season_year = season.split("-")[0]
        season_id = f"2{season_year}"  # NBA uses format like "22024" for 2024-25
        
        logger.info(f"Fetching {season_type} games for {season}")
        
        if team_ids:
            # Fetch games for each team
            for team_id in team_ids:
                try:
                    gamefinder = leaguegamefinder.LeagueGameFinder(
                        team_id_nullable=team_id,
                        season_nullable=season,
                        season_type_nullable=season_type,
                        league_id_nullable="00",  # NBA
                    )
                    df = gamefinder.get_data_frames()[0]
                    
                    for _, row in df.iterrows():
                        game_id = row["GAME_ID"]
                        if game_id in seen_game_ids:
                            continue
                        seen_game_ids.add(game_id)
                        
                        game = self._parse_game_row(row, season)
                        if game:
                            games.append(game)
                    
                    self._delay()

                except Exception as e:
                    if "Expecting Value" not in str(e):
                        logging.warning(f"Error fetching games for team {team_id}: {e}")
                    continue
                    # logger.warning(f"Error fetching games for team {team_id}: {e}")
                    # continue
        else:
            # Fetch all games
            try:
                gamefinder = leaguegamefinder.LeagueGameFinder(
                    season_nullable=season,
                    season_type_nullable=season_type,
                    league_id_nullable="00",
                )
                df = gamefinder.get_data_frames()[0]
                
                for _, row in df.iterrows():
                    game_id = row["GAME_ID"]
                    if game_id in seen_game_ids:
                        continue
                    seen_game_ids.add(game_id)
                    
                    game = self._parse_game_row(row, season)
                    if game:
                        games.append(game)
                        
            except Exception as e:
                logger.error(f"Error fetching all games: {e}")
        
        # Sort by date
        games.sort(key=lambda g: g.game_date)
        
        logger.info(f"Found {len(games)} games")
        return games
    
    def _parse_game_row(self, row: pd.Series, season: str) -> Optional[Game]:
        """Parse a game row from the API response."""
        try:
            game_id = row["GAME_ID"]
            matchup = row["MATCHUP"]  # e.g., "BOS vs. NYK" or "BOS @ NYK"
            team_abbrev = row["TEAM_ABBREVIATION"]
            team_id = row["TEAM_ID"]
            
            # Parse matchup to determine home/away
            if " vs. " in matchup:
                # This team is home
                parts = matchup.split(" vs. ")
                home_abbrev = parts[0]
                away_abbrev = parts[1]
            elif " @ " in matchup:
                # This team is away
                parts = matchup.split(" @ ")
                away_abbrev = parts[0]
                home_abbrev = parts[1]
            else:
                logger.warning(f"Unknown matchup format: {matchup}")
                return None
            
            # Get team info
            home_info = get_team_by_abbrev(home_abbrev)
            away_info = get_team_by_abbrev(away_abbrev)
            
            if not home_info or not away_info:
                logger.warning(f"Unknown team in matchup: {matchup}")
                return None
            
            # Parse date
            game_date_str = row["GAME_DATE"]
            game_date = datetime.strptime(game_date_str, "%Y-%m-%d")
            # Set a default game time of 7:30 PM ET (approximate)
            game_date = game_date.replace(hour=19, minute=30)
            
            # Check if completed
            wl = row.get("WL")
            completed = wl is not None and wl != ""
            
            # Get scores if completed
            home_score = None
            away_score = None
            if completed:
                pts = row.get("PTS")
                if pts is not None:
                    if team_abbrev == home_abbrev:
                        home_score = int(pts)
                    else:
                        away_score = int(pts)
            
            return Game(
                game_id=game_id,
                game_date=game_date,
                home_team_id=home_info["id"],
                home_team=home_abbrev,
                home_team_name=home_info["name"],
                away_team_id=away_info["id"],
                away_team=away_abbrev,
                away_team_name=away_info["name"],
                home_score=home_score,
                away_score=away_score,
                completed=completed,
                season=season,
                season_type=row.get("SEASON_TYPE", "Regular Season") if "SEASON_TYPE" in row else "Regular Season",
            )
            
        except Exception as e:
            logger.warning(f"Error parsing game row: {e}")
            return None
    
    def get_full_season_schedule(
        self,
        season: str,
        team_ids: Optional[list[int]] = None,
        include_preseason: bool = False,
        include_playoffs: bool = True,
    ) -> list[Game]:
        """
        Get the full season schedule including regular season and optionally playoffs.
        
        Args:
            season: Season string (e.g., "2024-25")
            team_ids: Optional list of team IDs to filter
            include_preseason: Include preseason games
            include_playoffs: Include playoff games
        """
        all_games = []
        seen_ids = set()
        
        season_types = ["Regular Season"]
        if include_preseason:
            season_types.insert(0, "Pre Season")
        if include_playoffs:
            season_types.append("Playoffs")
        
        for season_type in season_types:
            try:
                games = self.get_season_games(season, team_ids, season_type)
                for game in games:
                    if game.game_id not in seen_ids:
                        seen_ids.add(game.game_id)
                        game.season_type = season_type
                        all_games.append(game)
            except Exception as e:
                logger.warning(f"Error fetching {season_type} games: {e}")
        
        all_games.sort(key=lambda g: g.game_date)
        return all_games
