import logging
from typing import List, Dict, Any, Optional
from database.session import SessionLocal, get_db_session
from database.models import Match, MatchShots, MatchEvent, Team

logger = logging.getLogger("footy.database.match")

def save_match_to_db(match_data: Dict[str, Any], season_year: int, match_number: int) -> Optional[int]:
    """
    Save a completed match to the database using SQLAlchemy.
    """
    def get_team_id(val):
        if hasattr(val, "team_id"):
            return val.team_id
        return int(val)

    date = match_data.get("date")
    score = match_data.get("score")
    home_team_id = get_team_id(match_data.get("home_team_id"))
    away_team_id = get_team_id(match_data.get("away_team_id"))

    if not date or date == "N/A":
        logger.warning(f"Skipping match: missing/invalid date in match_data: {match_data}")
        return None
    if not isinstance(score, (list, tuple)) or len(score) != 2:
        logger.warning(f"Skipping match: missing/invalid score in match_data: {match_data}")
        return None
    if not isinstance(home_team_id, int) or not isinstance(away_team_id, int):
        logger.warning(f"Skipping match: missing/invalid team ids in match_data: {match_data}")
        return None

    try:
        with get_db_session() as db:
            match_obj = Match(
                match_number=match_number,
                date=date,
                season_year=season_year,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_goals=score[0],
                away_goals=score[1],
                home_possession=match_data.get("possession", [0, 0])[0],
                away_possession=match_data.get("possession", [0, 0])[1],
                weather=match_data.get("weather", "sunny"),
                intensity=match_data.get("intensity", "normal"),
                home_passes_attempted=match_data.get("passes_attempted", [0, 0])[0],
                away_passes_attempted=match_data.get("passes_attempted", [0, 0])[1],
                home_passes_completed=match_data.get("passes_completed", [0, 0])[0],
                away_passes_completed=match_data.get("passes_completed", [0, 0])[1],
                home_fouls=match_data.get("fouls", [0, 0])[0],
                away_fouls=match_data.get("fouls", [0, 0])[1],
                home_corners=match_data.get("corners", [0, 0])[0],
                away_corners=match_data.get("corners", [0, 0])[1],
                home_offsides=match_data.get("offsides", [0, 0])[0],
                away_offsides=match_data.get("offsides", [0, 0])[1]
            )
            db.add(match_obj)
            db.flush()
            match_id = match_obj.match_id

            # Save shots
            shots = match_data.get("shots", [0, 0])
            shots_on_target = match_data.get("shots_on_target", [0, 0])
            home_shot = MatchShots(match_id=match_id, team='home', total=shots[0], on_target=shots_on_target[0])
            away_shot = MatchShots(match_id=match_id, team='away', total=shots[1], on_target=shots_on_target[1])
            db.add(home_shot)
            db.add(away_shot)

            # Save events
            for event in match_data.get("events", []):
                if isinstance(event, str):
                    evt = MatchEvent(match_id=match_id, minute=0, type='forfeit', details=event)
                else:
                    evt = MatchEvent(
                        match_id=match_id,
                        minute=getattr(event, 'minute', 0),
                        type=getattr(event, 'type', 'unknown'),
                        player=getattr(event, 'player', ''),
                        team=getattr(event, 'team', ''),
                        details=getattr(event, 'details', '')
                    )
                db.add(evt)

            return match_id
    except Exception as e:
        logger.error(f"Database error saving match: {e}")
        return None

def get_matches_for_season(season_year: int) -> List[Dict[str, Any]]:
    """
    Retrieve all matches for a given season from the database.
    """
    db = SessionLocal()
    try:
        results = db.query(Match, Team.name.label("home_team_name")).join(
            Team, Match.home_team_id == Team.team_id
        ).filter(Match.season_year == season_year).order_by(Match.match_number).all()

        matches_list = []
        for m, home_name in results:
            away_team = db.query(Team).filter(Team.team_id == m.away_team_id).first()
            away_name = away_team.name if away_team else "Unknown"
            match_dict = {
                "match_id": m.match_id,
                "match_number": m.match_number,
                "date": m.date,
                "season_year": m.season_year,
                "home_team_id": m.home_team_id,
                "away_team_id": m.away_team_id,
                "home_team_name": home_name,
                "away_team_name": away_name,
                "home_goals": m.home_goals,
                "away_goals": m.away_goals,
                "home_possession": m.home_possession,
                "away_possession": m.away_possession,
                "weather": m.weather,
                "intensity": m.intensity,
                "home_passes_attempted": m.home_passes_attempted,
                "away_passes_attempted": m.away_passes_attempted,
                "home_passes_completed": m.home_passes_completed,
                "away_passes_completed": m.away_passes_completed,
                "home_fouls": m.home_fouls,
                "away_fouls": m.away_fouls,
                "home_corners": m.home_corners,
                "away_corners": m.away_corners,
                "home_offsides": m.home_offsides,
                "away_offsides": m.away_offsides,
            }
            matches_list.append(match_dict)
        return matches_list
    except Exception as e:
        logger.error(f"Database error fetching matches for season: {e}")
        return []
    finally:
        db.close()

def get_match_details(match_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve full details for a single match from the database.
    """
    db = SessionLocal()
    try:
        m = db.query(Match).filter(Match.match_id == match_id).first()
        if not m:
            return None

        home_team = db.query(Team).filter(Team.team_id == m.home_team_id).first()
        away_team = db.query(Team).filter(Team.team_id == m.away_team_id).first()

        match_details = {
            "match_id": m.match_id,
            "match_number": m.match_number,
            "date": m.date,
            "season_year": m.season_year,
            "home_team_id": m.home_team_id,
            "away_team_id": m.away_team_id,
            "home_team_name": home_team.name if home_team else "Unknown",
            "away_team_name": away_team.name if away_team else "Unknown",
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "home_possession": m.home_possession,
            "away_possession": m.away_possession,
            "weather": m.weather,
            "intensity": m.intensity,
            "home_passes_attempted": m.home_passes_attempted,
            "away_passes_attempted": m.away_passes_attempted,
            "home_passes_completed": m.home_passes_completed,
            "away_passes_completed": m.away_passes_completed,
            "home_fouls": m.home_fouls,
            "away_fouls": m.away_fouls,
            "home_corners": m.home_corners,
            "away_corners": m.away_corners,
            "home_offsides": m.home_offsides,
            "away_offsides": m.away_offsides,
        }

        # Shots
        shots_rows = db.query(MatchShots).filter(MatchShots.match_id == match_id).all()
        match_details["shots"] = {
            row.team: {"total": row.total, "on_target": row.on_target} for row in shots_rows
        }

        # Events
        events_rows = db.query(MatchEvent).filter(MatchEvent.match_id == match_id).order_by(MatchEvent.minute).all()
        match_details["events"] = [
            {
                "event_id": row.event_id,
                "minute": row.minute,
                "type": row.type,
                "player": row.player,
                "team": row.team,
                "details": row.details
            }
            for row in events_rows
        ]

        return match_details
    except Exception as e:
        logger.error(f"Database error fetching match details: {e}")
        return None
    finally:
        db.close()

