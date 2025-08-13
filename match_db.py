import sqlite3
from typing import List, Dict, Any

DB_FILE = "football_sim.db"

def get_db_connection():
    """Create and return a database connection."""
    return sqlite3.connect(DB_FILE)

def save_match_to_db(match_data: Dict[str, Any], season_year: int, match_number: int):
    """
    Save a completed match to the database.
    
    Args:
        match_data (dict): Dictionary containing all match details.
        season_year (int): The year the season took place.
        match_number (int): The match number in the season.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Insert into Match table
        cursor.execute("""
            INSERT INTO Match (
                match_number, date, season_year, home_team_id, away_team_id,
                home_goals, away_goals, home_possession, away_possession,
                weather, intensity,
                home_passes_attempted, away_passes_attempted,
                home_passes_completed, away_passes_completed,
                home_fouls, away_fouls,
                home_corners, away_corners,
                home_offsides, away_offsides
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_number,
            match_data.get("date", "N/A"),
            season_year,
            match_data["home_team_id"],
            match_data["away_team_id"],
            match_data["score"][0],
            match_data["score"][1],
            match_data["possession"][0],
            match_data["possession"][1],
            match_data["weather"],
            match_data.get("intensity", "normal"),
            match_data.get("passes_attempted", [0, 0])[0],
            match_data.get("passes_attempted", [0, 0])[1],
            match_data.get("passes_completed", [0, 0])[0],
            match_data.get("passes_completed", [0, 0])[1],
            match_data.get("fouls", [0, 0])[0],
            match_data.get("fouls", [0, 0])[1],
            match_data.get("corners", [0, 0])[0],
            match_data.get("corners", [0, 0])[1],
            match_data.get("offsides", [0, 0])[0],
            match_data.get("offsides", [0, 0])[1]
        ))
        match_id = cursor.lastrowid

        # 2. Insert into MatchShots table
        cursor.execute("""
            INSERT INTO MatchShots (match_id, team, total, on_target)
            VALUES (?, 'home', ?, ?)
        """, (match_id, match_data["shots"][0], match_data["shots_on_target"][0]))
        
        cursor.execute("""
            INSERT INTO MatchShots (match_id, team, total, on_target)
            VALUES (?, 'away', ?, ?)
        """, (match_id, match_data["shots"][1], match_data["shots_on_target"][1]))

        # 3. Insert into MatchEvent table
        for event in match_data.get("events", []):
            if isinstance(event, str):
                cursor.execute("""
                    INSERT INTO MatchEvent (match_id, minute, type, details)
                    VALUES (?, ?, ?, ?)
                """, (match_id, 0, 'forfeit', event))
            else:
                cursor.execute("""
                    INSERT INTO MatchEvent (match_id, minute, type, player, team, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    match_id,
                    event.minute,
                    event.type,
                    event.player,
                    event.team,
                    event.details
                ))
            
        # 4. Insert lineups and formations (assuming new tables)
        # This part will require schema changes to be implemented first
        # Example for home team lineup:
        # for player, position in zip(match_data["home_lineup"], match_data["home_positions"]):
        #     cursor.execute("""
        #         INSERT INTO MatchLineup (match_id, team_id, player_id, position)
        #         VALUES (?, ?, ?, ?)
        #     """, (match_id, match_data["home_team_id"], player.player_id, position))

        conn.commit()
        #print(f"Successfully saved match {match_id} to the database.")
        return match_id

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_matches_for_season(season_year: int) -> List[Dict[str, Any]]:
    """
    Retrieve all matches for a given season from the database.
    
    Args:
        season_year (int): The season year to retrieve matches for.
        
    Returns:
        List of dictionaries, where each dictionary is a match.
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT m.*, ht.name as home_team_name, at.name as away_team_name
            FROM Match m
            JOIN Team ht ON m.home_team_id = ht.team_id
            JOIN Team at ON m.away_team_id = at.team_id
            WHERE m.season_year = ?
            ORDER BY m.match_number
        """, (season_year,))
        
        matches = [dict(row) for row in cursor.fetchall()]
        return matches
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        conn.close()

def get_match_details(match_id: int) -> Dict[str, Any]:
    """
    Retrieve full details for a single match from the database.
    
    Args:
        match_id (int): The ID of the match to retrieve.
        
    Returns:
        A dictionary containing all details of the match.
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    match_details = {}
    
    try:
        # Get main match data
        cursor.execute("""
            SELECT m.*, ht.name as home_team_name, at.name as away_team_name
            FROM Match m
            JOIN Team ht ON m.home_team_id = ht.team_id
            JOIN Team at ON m.away_team_id = at.team_id
            WHERE m.match_id = ?
        """, (match_id,))
        match_info = cursor.fetchone()
        if not match_info:
            return None
        match_details.update(dict(match_info))
        
        # Get shots data
        cursor.execute("SELECT * FROM MatchShots WHERE match_id = ?", (match_id,))
        shots_data = cursor.fetchall()
        match_details["shots"] = {row["team"]: {"total": row["total"], "on_target": row["on_target"]} for row in shots_data}
        
        # Get events data
        cursor.execute("SELECT * FROM MatchEvent WHERE match_id = ? ORDER BY minute", (match_id,))
        events_data = cursor.fetchall()
        match_details["events"] = [dict(row) for row in events_data]
        
        # Get lineup data (from placeholder tables)
        # This will need to be updated once the schema is finalized
        # cursor.execute("SELECT * FROM MatchLineup WHERE match_id = ?", (match_id,))
        # lineup_data = cursor.fetchall()
        # match_details["lineups"] = [dict(row) for row in lineup_data]
        
        return match_details
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        conn.close()
