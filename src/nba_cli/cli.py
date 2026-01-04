"""Command-line interface for NBA CLI."""

import logging
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .api import NBAClient
from .calendar import CalendarManager
from .config import (
    Config,
    NBA_TEAMS,
    NBA_CONFERENCES,
    NBA_DIVISIONS,
    get_team_by_name,
    get_team_by_abbrev,
    get_teams_by_conference,
    get_teams_by_division,
    load_config,
    save_config,
    get_config_path,
    get_calendars_dir,
)

console = Console()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug: bool):
    """NBA Schedule Tracker - Get NBA games on your calendar."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
def init():
    """Initialize configuration with interactive setup."""
    console.print(Panel.fit(
        "[bold blue]NBA CLI Setup[/bold blue]\n"
        "Let's configure your NBA schedule tracker.",
        border_style="blue"
    ))
    
    config = load_config()
    
    # Season
    current = Config.get_current_season()
    season = click.prompt("Season", default=current)
    config.season = season
    
    console.print("\n[bold]What do you want to track?[/bold]")
    console.print("1. Specific teams")
    console.print("2. Conferences (East/West)")
    console.print("3. Divisions")
    console.print("4. All of the above")
    
    choice = click.prompt("Choice", type=int, default=1)
    
    if choice in [1, 4]:
        console.print("\n[bold]Enter team names or abbreviations (comma-separated):[/bold]")
        console.print("Example: LAL, Celtics, GSW")
        teams_input = click.prompt("Teams", default="")
        
        if teams_input:
            teams = []
            for t in teams_input.split(","):
                t = t.strip()
                if not t:
                    continue
                
                # Try abbreviation first
                if get_team_by_abbrev(t):
                    teams.append(t.upper())
                else:
                    # Try name match
                    result = get_team_by_name(t)
                    if result:
                        teams.append(result[0])
                    else:
                        console.print(f"[yellow]Unknown team: {t}[/yellow]")
            
            config.tracked.teams = teams
    
    if choice in [2, 4]:
        console.print("\n[bold]Select conferences:[/bold]")
        console.print("Available: East, West")
        conf_input = click.prompt("Conferences (comma-separated)", default="")
        
        if conf_input:
            confs = []
            for c in conf_input.split(","):
                c = c.strip().capitalize()
                if c in ["East", "West"]:
                    confs.append(c)
            config.tracked.conferences = confs
    
    if choice in [3, 4]:
        console.print("\n[bold]Select divisions:[/bold]")
        console.print("East: Atlantic, Central, Southeast")
        console.print("West: Northwest, Pacific, Southwest")
        div_input = click.prompt("Divisions (comma-separated)", default="")
        
        if div_input:
            all_divs = ["Atlantic", "Central", "Southeast", "Northwest", "Pacific", "Southwest"]
            divs = []
            for d in div_input.split(","):
                d = d.strip().capitalize()
                if d in all_divs:
                    divs.append(d)
            config.tracked.divisions = divs
    
    save_config(config)
    console.print(f"\n[green]Configuration saved to {get_config_path()}[/green]")


@cli.command()
@click.option("-c", "--conference", help="Filter by conference (East/West)")
@click.option("-d", "--division", help="Filter by division")
@click.option("-s", "--search", help="Search by team name")
def teams(conference: str, division: str, search: str):
    """List all NBA teams."""
    table = Table(title="NBA Teams")
    table.add_column("Abbrev", style="cyan")
    table.add_column("Team Name", style="white")
    table.add_column("Conference", style="green")
    table.add_column("Division", style="yellow")
    
    for abbrev, info in sorted(NBA_TEAMS.items(), key=lambda x: (x[1]["conference"], x[1]["division"], x[1]["name"])):
        # Apply filters
        if conference and info["conference"].lower() != conference.lower():
            continue
        if division and info["division"].lower() != division.lower():
            continue
        if search and search.lower() not in info["name"].lower() and search.lower() != abbrev.lower():
            continue
        
        table.add_row(
            abbrev,
            info["name"],
            info["conference"],
            info["division"],
        )
    
    console.print(table)


@cli.command()
def conferences():
    """List NBA conferences and divisions."""
    for conf in NBA_CONFERENCES:
        console.print(f"\n[bold blue]{conf}ern Conference[/bold blue]")
        
        for div in NBA_DIVISIONS[conf]:
            console.print(f"  [yellow]{div} Division:[/yellow]")
            div_teams = get_teams_by_division(div)
            for abbrev, info in div_teams:
                console.print(f"    {abbrev} - {info['name']}")


@cli.command()
@click.argument("team")
def track(team: str):
    """Add a team to tracking list."""
    config = load_config()
    
    # Check if it's a conference
    if team.capitalize() in ["East", "West"]:
        if team.capitalize() not in config.tracked.conferences:
            config.tracked.conferences.append(team.capitalize())
            save_config(config)
            console.print(f"[green]Now tracking {team.capitalize()}ern Conference[/green]")
        else:
            console.print(f"[yellow]Already tracking {team.capitalize()}ern Conference[/yellow]")
        return
    
    # Check if it's a division
    all_divs = ["Atlantic", "Central", "Southeast", "Northwest", "Pacific", "Southwest"]
    for div in all_divs:
        if team.lower() == div.lower():
            if div not in config.tracked.divisions:
                config.tracked.divisions.append(div)
                save_config(config)
                console.print(f"[green]Now tracking {div} Division[/green]")
            else:
                console.print(f"[yellow]Already tracking {div} Division[/yellow]")
            return
    
    # Try as team
    if get_team_by_abbrev(team):
        abbrev = team.upper()
    else:
        result = get_team_by_name(team)
        if result:
            abbrev = result[0]
        else:
            console.print(f"[red]Unknown team: {team}[/red]")
            console.print("Use 'nba-cli teams' to see available teams")
            return
    
    if abbrev not in config.tracked.teams:
        config.tracked.teams.append(abbrev)
        save_config(config)
        team_info = get_team_by_abbrev(abbrev)
        console.print(f"[green]Now tracking {team_info['name']} ({abbrev})[/green]")
    else:
        team_info = get_team_by_abbrev(abbrev)
        console.print(f"[yellow]Already tracking {team_info['name']}[/yellow]")


@cli.command()
@click.argument("team")
def untrack(team: str):
    """Remove a team from tracking list."""
    config = load_config()
    
    # Check conferences
    if team.capitalize() in config.tracked.conferences:
        config.tracked.conferences.remove(team.capitalize())
        save_config(config)
        console.print(f"[green]Removed {team.capitalize()}ern Conference from tracking[/green]")
        return
    
    # Check divisions
    for div in config.tracked.divisions:
        if team.lower() == div.lower():
            config.tracked.divisions.remove(div)
            save_config(config)
            console.print(f"[green]Removed {div} Division from tracking[/green]")
            return
    
    # Try as team
    abbrev = team.upper() if get_team_by_abbrev(team) else None
    if not abbrev:
        result = get_team_by_name(team)
        if result:
            abbrev = result[0]
    
    if abbrev and abbrev in config.tracked.teams:
        config.tracked.teams.remove(abbrev)
        save_config(config)
        team_info = get_team_by_abbrev(abbrev)
        console.print(f"[green]Removed {team_info['name']} from tracking[/green]")
    else:
        console.print(f"[yellow]Not tracking: {team}[/yellow]")


@cli.command()
def status():
    """Show current configuration."""
    config = load_config()
    
    console.print(Panel.fit(
        f"[bold]NBA CLI Configuration[/bold]\n"
        f"Config file: {get_config_path()}",
        border_style="blue"
    ))
    
    console.print(f"\n[bold]Season:[/bold] {config.season}")
    
    if config.tracked.teams:
        console.print(f"\n[bold]Tracked Teams:[/bold]")
        for abbrev in config.tracked.teams:
            info = get_team_by_abbrev(abbrev)
            if info:
                console.print(f"  - {info['name']} ({abbrev})")
    
    if config.tracked.conferences:
        console.print(f"\n[bold]Tracked Conferences:[/bold]")
        for conf in config.tracked.conferences:
            console.print(f"  - {conf}ern Conference")
    
    if config.tracked.divisions:
        console.print(f"\n[bold]Tracked Divisions:[/bold]")
        for div in config.tracked.divisions:
            console.print(f"  - {div} Division")
    
    if config.tracked.is_empty():
        console.print("\n[yellow]No teams tracked. Use 'nba-cli track <team>' to add teams.[/yellow]")


@cli.command()
@click.option("--include-preseason", is_flag=True, help="Include preseason games")
@click.option("--include-playoffs/--no-playoffs", default=True, help="Include playoff games")
def sync(include_preseason: bool, include_playoffs: bool):
    """Fetch schedule and generate calendar files."""
    config = load_config()
    
    if config.tracked.is_empty():
        console.print("[yellow]No teams tracked. Use 'nba-cli track <team>' first.[/yellow]")
        return
    
    console.print(f"Fetching {config.season} schedule...")
    
    client = NBAClient()
    team_ids = config.tracked.get_all_team_ids()
    
    games = client.get_full_season_schedule(
        season=config.season,
        team_ids=team_ids if team_ids else None,
        include_preseason=include_preseason,
        include_playoffs=include_playoffs,
    )
    
    console.print(f"Found {len(games)} games")
    
    if not games:
        console.print("[yellow]No games found. The season may not have started yet.[/yellow]")
        return
    
    console.print("Generating calendar files...")
    
    manager = CalendarManager()
    generated = manager.generate_all(
        games=games,
        tracked_teams=config.tracked.teams,
        tracked_conferences=config.tracked.conferences,
        tracked_divisions=config.tracked.divisions,
    )
    
    console.print(f"\nGenerated {len(generated)} calendar file(s):")
    for path in generated:
        console.print(f"  {path}")
    
    console.print("\n[bold]To import into Google Calendar:[/bold]")
    console.print("  1. Go to calendar.google.com")
    console.print("  2. Click the gear icon > Settings")
    console.print("  3. Import & Export > Import")
    console.print("  4. Select the .ics file and choose a calendar")


@cli.command()
@click.option("-n", "--limit", default=10, help="Number of games to show")
def schedule(limit: int):
    """View upcoming games."""
    config = load_config()
    
    if config.tracked.is_empty():
        console.print("[yellow]No teams tracked. Use 'nba-cli track <team>' first.[/yellow]")
        return
    
    client = NBAClient()
    team_ids = config.tracked.get_all_team_ids()
    
    console.print(f"Fetching schedule for {config.season}...")
    
    games = client.get_full_season_schedule(
        season=config.season,
        team_ids=team_ids if team_ids else None,
    )
    
    # Filter to upcoming games
    now = datetime.now()
    upcoming = [g for g in games if g.game_date >= now][:limit]
    
    if not upcoming:
        console.print("[yellow]No upcoming games found.[/yellow]")
        return
    
    table = Table(title=f"Upcoming Games ({config.season})")
    table.add_column("Date", style="cyan")
    table.add_column("Time", style="green")
    table.add_column("Matchup", style="white")
    table.add_column("Type", style="yellow")
    
    for game in upcoming:
        table.add_row(
            game.game_date.strftime("%a %b %d"),
            game.game_date.strftime("%I:%M %p"),
            game.matchup_full,
            game.season_type if game.season_type != "Regular Season" else "",
        )
    
    console.print(table)


@cli.command()
def debug():
    """Show debug information and raw API response."""
    from nba_api.stats.endpoints import leaguegamefinder
    
    config = load_config()
    
    console.print("[bold]Debug Info[/bold]")
    console.print(f"Season: {config.season}")
    console.print(f"Config path: {get_config_path()}")
    console.print(f"Calendars dir: {get_calendars_dir()}")
    
    console.print("\n[bold]Fetching sample data...[/bold]")
    
    try:
        gamefinder = leaguegamefinder.LeagueGameFinder(
            season_nullable=config.season,
            season_type_nullable="Regular Season",
            league_id_nullable="00",
        )
        df = gamefinder.get_data_frames()[0]
        
        console.print(f"\nTotal rows: {len(df)}")
        console.print(f"Columns: {list(df.columns)}")
        
        if len(df) > 0:
            console.print("\n[bold]Sample row:[/bold]")
            row = df.iloc[0]
            for col in df.columns:
                console.print(f"  {col}: {row[col]}")
                
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    cli()
