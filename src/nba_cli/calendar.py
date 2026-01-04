"""Calendar generation for NBA schedules."""

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from icalendar import Calendar, Event, Alarm

from .api import Game
from .config import NBA_TEAMS, get_team_by_abbrev, get_calendars_dir

logger = logging.getLogger(__name__)


def create_game_event(
    game: Game,
    reminder_minutes: int = 60,
) -> Event:
    """
    Create an iCalendar event for a game.
    
    Args:
        game: Game object
        reminder_minutes: Minutes before game to trigger reminder
    """
    event = Event()
    
    # Create unique ID
    uid_base = f"nba-{game.season}-{game.game_id}"
    uid = hashlib.md5(uid_base.encode()).hexdigest()
    event.add("uid", f"{uid}@nba-cli")
    
    # Title
    if game.completed and game.home_score is not None and game.away_score is not None:
        summary = f"{game.away_team} {game.away_score} @ {game.home_team} {game.home_score}"
    else:
        summary = f"{game.away_team} @ {game.home_team}"
    event.add("summary", summary)
    
    # Time - NBA games are typically 2.5-3 hours
    event.add("dtstart", game.game_date)
    event.add("dtend", game.game_date + timedelta(hours=3))
    
    # Location
    if game.arena:
        event.add("location", game.arena)
    
    # Description
    description_parts = [
        f"{game.away_team_name} @ {game.home_team_name}",
        f"Season: {game.season}",
    ]
    
    if game.season_type != "Regular Season":
        description_parts.append(f"Type: {game.season_type}")
    
    if game.completed:
        if game.home_score is not None and game.away_score is not None:
            description_parts.append(f"Final: {game.away_team} {game.away_score} - {game.home_score} {game.home_team}")
    
    event.add("description", "\n".join(description_parts))
    
    # Categories
    categories = ["NBA", "Basketball"]
    if game.season_type == "Playoffs":
        categories.append("Playoffs")
    event.add("categories", categories)
    
    # Status
    if game.completed:
        event.add("status", "CONFIRMED")
    else:
        event.add("status", "TENTATIVE")
    
    # Reminder (only for future games)
    if not game.completed and reminder_minutes > 0:
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", f"NBA: {game.matchup} starting soon")
        alarm.add("trigger", timedelta(minutes=-reminder_minutes))
        event.add_component(alarm)
    
    # Timestamps
    event.add("dtstamp", datetime.now())
    event.add("created", datetime.now())
    
    return event


def generate_team_calendar(
    games: list[Game],
    team_abbrev: str,
    calendar_name: Optional[str] = None,
    reminder_minutes: int = 60,
) -> Calendar:
    """
    Generate a calendar for a specific team.
    
    Args:
        games: List of all games
        team_abbrev: Team abbreviation (e.g., "LAL")
        calendar_name: Optional custom calendar name
        reminder_minutes: Minutes before game for reminder
    """
    team_info = get_team_by_abbrev(team_abbrev)
    if not team_info:
        raise ValueError(f"Unknown team: {team_abbrev}")
    
    cal = Calendar()
    cal.add("prodid", "-//NBA CLI//nba-cli//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calendar_name or f"NBA - {team_info['name']}")
    cal.add("x-wr-timezone", "America/New_York")
    
    # Filter games for this team
    team_games = [g for g in games if g.involves_team(team_abbrev)]
    
    for game in team_games:
        event = create_game_event(game, reminder_minutes)
        cal.add_component(event)
    
    logger.info(f"Created calendar with {len(team_games)} events for {team_abbrev}")
    return cal


def generate_conference_calendar(
    games: list[Game],
    conference: str,
    calendar_name: Optional[str] = None,
    reminder_minutes: int = 60,
) -> Calendar:
    """
    Generate a calendar for a conference.
    
    Args:
        games: List of all games
        conference: Conference name ("East" or "West")
        calendar_name: Optional custom calendar name
        reminder_minutes: Minutes before game for reminder
    """
    conf = conference.capitalize()
    
    cal = Calendar()
    cal.add("prodid", "-//NBA CLI//nba-cli//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calendar_name or f"NBA - {conf}ern Conference")
    cal.add("x-wr-timezone", "America/New_York")
    
    # Get teams in this conference
    conf_teams = [abbrev for abbrev, info in NBA_TEAMS.items() 
                  if info["conference"] == conf]
    
    # Filter games where at least one team is from this conference
    conf_games = []
    seen_ids = set()
    for game in games:
        if game.game_id in seen_ids:
            continue
        if game.home_team in conf_teams or game.away_team in conf_teams:
            conf_games.append(game)
            seen_ids.add(game.game_id)
    
    for game in conf_games:
        event = create_game_event(game, reminder_minutes)
        cal.add_component(event)
    
    logger.info(f"Created calendar with {len(conf_games)} events for {conf}ern Conference")
    return cal


def generate_division_calendar(
    games: list[Game],
    division: str,
    calendar_name: Optional[str] = None,
    reminder_minutes: int = 60,
) -> Calendar:
    """
    Generate a calendar for a division.
    
    Args:
        games: List of all games
        division: Division name (e.g., "Atlantic", "Pacific")
        calendar_name: Optional custom calendar name
        reminder_minutes: Minutes before game for reminder
    """
    div = division.capitalize()
    
    cal = Calendar()
    cal.add("prodid", "-//NBA CLI//nba-cli//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calendar_name or f"NBA - {div} Division")
    cal.add("x-wr-timezone", "America/New_York")
    
    # Get teams in this division
    div_teams = [abbrev for abbrev, info in NBA_TEAMS.items() 
                 if info["division"] == div]
    
    # Filter games where at least one team is from this division
    div_games = []
    seen_ids = set()
    for game in games:
        if game.game_id in seen_ids:
            continue
        if game.home_team in div_teams or game.away_team in div_teams:
            div_games.append(game)
            seen_ids.add(game.game_id)
    
    for game in div_games:
        event = create_game_event(game, reminder_minutes)
        cal.add_component(event)
    
    logger.info(f"Created calendar with {len(div_games)} events for {div} Division")
    return cal


def export_calendar(cal: Calendar, filepath: Path) -> None:
    """Export calendar to ICS file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, "wb") as f:
        f.write(cal.to_ical())
    
    logger.info(f"Exported calendar to {filepath}")


class CalendarManager:
    """Manages calendar generation and export."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or get_calendars_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_all(
        self,
        games: list[Game],
        tracked_teams: list[str],
        tracked_conferences: list[str],
        tracked_divisions: list[str],
        reminder_minutes: int = 60,
    ) -> list[Path]:
        """
        Generate all configured calendars.
        
        Returns list of generated file paths.
        """
        generated = []
        
        # Generate team calendars
        for abbrev in tracked_teams:
            try:
                cal = generate_team_calendar(games, abbrev, reminder_minutes=reminder_minutes)
                filepath = self.output_dir / f"nba_{abbrev.lower()}.ics"
                export_calendar(cal, filepath)
                generated.append(filepath)
            except Exception as e:
                logger.error(f"Error generating calendar for {abbrev}: {e}")
        
        # Generate conference calendars
        for conf in tracked_conferences:
            try:
                cal = generate_conference_calendar(games, conf, reminder_minutes=reminder_minutes)
                filepath = self.output_dir / f"nba_{conf.lower()}.ics"
                export_calendar(cal, filepath)
                generated.append(filepath)
            except Exception as e:
                logger.error(f"Error generating calendar for {conf}: {e}")
        
        # Generate division calendars
        for div in tracked_divisions:
            try:
                cal = generate_division_calendar(games, div, reminder_minutes=reminder_minutes)
                filepath = self.output_dir / f"nba_{div.lower()}.ics"
                export_calendar(cal, filepath)
                generated.append(filepath)
            except Exception as e:
                logger.error(f"Error generating calendar for {div}: {e}")
        
        # Generate combined calendar if tracking anything
        if tracked_teams or tracked_conferences or tracked_divisions:
            try:
                cal = Calendar()
                cal.add("prodid", "-//NBA CLI//nba-cli//EN")
                cal.add("version", "2.0")
                cal.add("calscale", "GREGORIAN")
                cal.add("method", "PUBLISH")
                cal.add("x-wr-calname", "NBA Schedule")
                cal.add("x-wr-timezone", "America/New_York")
                
                seen_ids = set()
                for game in games:
                    if game.game_id in seen_ids:
                        continue
                    seen_ids.add(game.game_id)
                    event = create_game_event(game, reminder_minutes)
                    cal.add_component(event)
                
                filepath = self.output_dir / "nba_schedule.ics"
                export_calendar(cal, filepath)
                generated.append(filepath)
                
                logger.info(f"Created combined calendar with {len(seen_ids)} events")
                
            except Exception as e:
                logger.error(f"Error generating combined calendar: {e}")
        
        return generated
