import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import aliased
from database.session import SessionLocal, get_db_session
from database.models import Match, MatchShots, MatchEvent, Team, Manager, Player, SimulationRun

logger = logging.getLogger("footy.database.match")

def save_match_to_db(
    match_data: Dict[str, Any],
    season_year: int,
    match_number: int,
    simulation_run_id: Optional[str] = None,
    video_url: Optional[str] = None
) -> Optional[int]:
    """
    Save a completed match to the database using SQLAlchemy with run-scoped identity.
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
        raise ValueError("Cannot persist a match without a valid date")
    if not isinstance(score, (list, tuple)) or len(score) != 2:
        raise ValueError("Cannot persist a match without a two-value score")
    if not isinstance(home_team_id, int) or not isinstance(away_team_id, int):
        raise ValueError("Cannot persist a match without integer team ids")

    def parse_team_stat(val, default_pair=(0, 0)):
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            return val[0], val[1]
        elif isinstance(val, dict):
            return val.get("home", default_pair[0]), val.get("away", default_pair[1])
        return default_pair

    h_pos, a_pos = parse_team_stat(match_data.get("possession"), (50, 50))
    h_att, a_att = parse_team_stat(match_data.get("passes_attempted"), (0, 0))
    h_cmp, a_cmp = parse_team_stat(match_data.get("passes_completed"), (0, 0))
    h_fouls, a_fouls = parse_team_stat(match_data.get("fouls"), (0, 0))
    h_corners, a_corners = parse_team_stat(match_data.get("corners"), (0, 0))
    h_offsides, a_offsides = parse_team_stat(match_data.get("offsides"), (0, 0))
    h_shots, a_shots = parse_team_stat(match_data.get("shots"), (0, 0))
    h_sot, a_sot = parse_team_stat(match_data.get("shots_on_target"), (0, 0))

    try:
        with get_db_session() as db:
            effective_run_id = simulation_run_id or match_data.get("simulation_run_id")
            effective_video_url = video_url or match_data.get("video_url")
            # A match number is only unique inside a simulation run.  The legacy
            # season key remains for records created before run isolation.
            match_query = db.query(Match).filter(Match.match_number == match_number)
            if effective_run_id:
                match_query = match_query.filter(
                    Match.simulation_run_id == effective_run_id,
                    Match.season_year == season_year,
                )
            else:
                match_query = match_query.filter(
                    Match.simulation_run_id.is_(None), Match.season_year == season_year
                )
            match_obj = match_query.first()

            if not match_obj:
                match_obj = Match(
                    match_number=match_number,
                    simulation_run_id=effective_run_id,
                    video_url=effective_video_url,
                    date=date,
                    season_year=season_year,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_goals=score[0],
                    away_goals=score[1],
                    home_possession=h_pos,
                    away_possession=a_pos,
                    weather=match_data.get("weather", "Sunny"),
                    intensity=str(match_data.get("intensity", "50")),
                    home_passes_attempted=h_att,
                    away_passes_attempted=a_att,
                    home_passes_completed=h_cmp,
                    away_passes_completed=a_cmp,
                    home_fouls=h_fouls,
                    away_fouls=a_fouls,
                    home_corners=h_corners,
                    away_corners=a_corners,
                    home_offsides=h_offsides,
                    away_offsides=a_offsides,
                    trace_file=match_data.get("trace_file") or match_data.get("trajectory_file") or match_data.get("trace_npz") or match_data.get("recorded_trace") or match_data.get("trace_dump"),
                )
                db.add(match_obj)
                db.flush()
            else:
                if effective_run_id:
                    match_obj.simulation_run_id = effective_run_id
                if effective_video_url:
                    match_obj.video_url = effective_video_url
                match_obj.date = date
                match_obj.home_team_id = home_team_id
                match_obj.away_team_id = away_team_id
                match_obj.home_goals = score[0]
                match_obj.away_goals = score[1]
                match_obj.home_possession = h_pos
                match_obj.away_possession = a_pos
                match_obj.weather = match_data.get("weather", "Sunny")
                match_obj.intensity = str(match_data.get("intensity", "50"))
                match_obj.home_passes_attempted = h_att
                match_obj.away_passes_attempted = a_att
                match_obj.home_passes_completed = h_cmp
                match_obj.away_passes_completed = a_cmp
                match_obj.home_fouls = h_fouls
                match_obj.away_fouls = a_fouls
                match_obj.home_corners = h_corners
                match_obj.away_corners = a_corners
                match_obj.home_offsides = h_offsides
                match_obj.away_offsides = a_offsides
                tf = match_data.get("trace_file") or match_data.get("trajectory_file") or match_data.get("trace_npz") or match_data.get("recorded_trace") or match_data.get("trace_dump")
                if tf:
                    match_obj.trace_file = tf
                db.flush()
                db.query(MatchShots).filter(MatchShots.match_id == match_obj.match_id).delete()
                db.query(MatchEvent).filter(MatchEvent.match_id == match_obj.match_id).delete()

            match_id = match_obj.match_id

            # Save shots
            db.add(MatchShots(match_id=match_id, team='home', total=h_shots, on_target=h_sot))
            db.add(MatchShots(match_id=match_id, team='away', total=a_shots, on_target=a_sot))

            # Save events
            for event in match_data.get("events", []):
                if isinstance(event, dict):
                    evt = MatchEvent(
                        match_id=match_id,
                        minute=event.get('minute', 0),
                        type=event.get('type', 'goal'),
                        player=event.get('player', 'Unknown'),
                        team=event.get('team', 'home'),
                        details=event.get('details', '')
                    )
                else:
                    evt = MatchEvent(
                        match_id=match_id,
                        minute=getattr(event, 'minute', 0),
                        type=getattr(event, 'type', 'goal'),
                        player=getattr(event, 'player', 'Unknown'),
                        team=getattr(event, 'team', 'home'),
                        details=getattr(event, 'details', '')
                    )
                db.add(evt)

            # Save lineups and bench if provided
            import json
            if match_data.get("home_lineup"):
                db.add(MatchEvent(
                    match_id=match_id,
                    minute=0,
                    type='home_lineup',
                    player=match_data.get('home_formation', '4-3-3'),
                    team='home',
                    details=json.dumps(match_data.get('home_lineup'))
                ))
            if match_data.get("away_lineup"):
                db.add(MatchEvent(
                    match_id=match_id,
                    minute=0,
                    type='away_lineup',
                    player=match_data.get('away_formation', '4-2-3-1'),
                    team='away',
                    details=json.dumps(match_data.get('away_lineup'))
                ))
            if match_data.get("home_bench"):
                db.add(MatchEvent(
                    match_id=match_id,
                    minute=0,
                    type='home_bench',
                    player='bench',
                    team='home',
                    details=json.dumps(match_data.get('home_bench'))
                ))
            if match_data.get("away_bench"):
                db.add(MatchEvent(
                    match_id=match_id,
                    minute=0,
                    type='away_bench',
                    player='bench',
                    team='away',
                    details=json.dumps(match_data.get('away_bench'))
                ))
            if match_data.get("substitutions"):
                db.add(MatchEvent(
                    match_id=match_id,
                    minute=0,
                    type='substitutions',
                    player='subs',
                    team='both',
                    details=json.dumps(match_data.get('substitutions'))
                ))

            return match_id
    except Exception as e:
        logger.error(f"Database error saving match: {e}")
        raise

def get_matches_for_season(season_year: int, simulation_run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve all matches for a given season from the database.
    Optimized with single-query aliased joins and video_url metadata.
    """
    db = SessionLocal()
    try:
        HomeTeam = aliased(Team)
        AwayTeam = aliased(Team)
        selected_run_id = simulation_run_id or db.query(Match.simulation_run_id).join(
            SimulationRun, Match.simulation_run_id == SimulationRun.run_id
        ).filter(
            Match.season_year == season_year
        ).order_by(SimulationRun.created_at.desc()).limit(1).scalar()
        query = db.query(
            Match,
            HomeTeam.name.label("home_team_name"),
            AwayTeam.name.label("away_team_name")
        ).outerjoin(
            HomeTeam, Match.home_team_id == HomeTeam.team_id
        ).outerjoin(
            AwayTeam, Match.away_team_id == AwayTeam.team_id
        ).filter(Match.season_year == season_year)
        if selected_run_id:
            query = query.filter(Match.simulation_run_id == selected_run_id)
        else:
            query = query.filter(Match.simulation_run_id.is_(None))
        results = query.order_by(Match.match_number).all()

        matches_list = []
        for m, home_name, away_name in results:
            vurl = m.video_url.replace("\\", "/") if m.video_url else None
            match_dict = {
                "match_id": m.match_id,
                "match_number": m.match_number,
                "simulation_run_id": m.simulation_run_id,
                "video_url": vurl,
                "date": m.date,
                "season_year": m.season_year,
                "home_team_id": m.home_team_id,
                "away_team_id": m.away_team_id,
                "home_team_name": home_name or "Home",
                "away_team_name": away_name or "Away",
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

def get_match_details(match_id: Any) -> Optional[Dict[str, Any]]:
    """
    Retrieve full details for a single match from the database.
    """
    db = SessionLocal()
    try:
        m = None
        # 1. Direct integer or integer-string lookup
        if isinstance(match_id, int) or (isinstance(match_id, str) and match_id.strip().isdigit()):
            int_id = int(match_id)
            m = db.query(Match).filter(Match.match_id == int_id).first()
            if m is None:
                latest_run = db.query(SimulationRun.run_id).order_by(
                    SimulationRun.created_at.desc()
                ).limit(1).scalar()
                fallback = db.query(Match).filter(Match.match_number == int_id)
                if latest_run:
                    fallback = fallback.filter(Match.simulation_run_id == latest_run)
                m = fallback.first()

        # 2. Formatted string identifier lookup
        if not m and isinstance(match_id, str):
            clean_str = match_id.strip()
            if clean_str.startswith("match_"):
                rest = clean_str[6:]
                if rest.isdigit():
                    int_id = int(rest)
                    m = db.query(Match).filter(
                        (Match.match_id == int_id) | (Match.match_number == int_id)
                    ).first()
                else:
                    parts = rest.split("_")
                    if len(parts) == 3 and all(p.isdigit() for p in parts):
                        # match_{season_year}_{home_team_id}_{away_team_id}
                        m = db.query(Match).filter(
                            Match.season_year == int(parts[0]),
                            Match.home_team_id == int(parts[1]),
                            Match.away_team_id == int(parts[2]),
                        ).first()
                    elif len(parts) == 2 and all(p.isdigit() for p in parts):
                        m = db.query(Match).filter(
                            Match.home_team_id == int(parts[0]),
                            Match.away_team_id == int(parts[1]),
                        ).first()

            if not m:
                # 3. Fallback to substring trace_file lookup
                m = db.query(Match).filter(Match.trace_file.like(f"%{clean_str}%")).first()

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
            "trace_file": m.trace_file,
            "home_lineup": [],
            "away_lineup": [],
            "home_bench": [],
            "away_bench": [],
            "substitutions": [],
        }

        # Shots (foreign key is Match.match_id)
        shots_rows = db.query(MatchShots).filter(MatchShots.match_id == m.match_id).all()
        match_details["shots"] = {
            row.team: {"total": row.total, "on_target": row.on_target} for row in shots_rows
        }

        # Events (foreign key is Match.match_id)
        events_rows = db.query(MatchEvent).filter(MatchEvent.match_id == m.match_id).order_by(MatchEvent.minute).all()
        user_events = [row for row in events_rows if row.type not in ('home_lineup', 'away_lineup', 'home_bench', 'away_bench', 'substitutions')]
        match_details["events"] = [
            {
                "event_id": row.event_id,
                "minute": row.minute,
                "type": row.type,
                "player": row.player,
                "team": row.team,
                "details": row.details
            }
            for row in user_events
        ]

        # Fetch Manager & Formations fallback
        home_mgr = db.query(Manager).filter(Manager.manager_id == home_team.manager_id).first() if home_team else None
        away_mgr = db.query(Manager).filter(Manager.manager_id == away_team.manager_id).first() if away_team else None
        
        home_formation = home_mgr.formation if home_mgr else "4-3-3"
        away_formation = away_mgr.formation if away_mgr else "4-2-3-1"
        match_details["home_formation"] = home_formation
        match_details["away_formation"] = away_formation

        # Check for stored exact match lineups, bench & substitutions
        home_lineup_evt = next((r for r in events_rows if r.type == 'home_lineup'), None)
        away_lineup_evt = next((r for r in events_rows if r.type == 'away_lineup'), None)
        home_bench_evt = next((r for r in events_rows if r.type == 'home_bench'), None)
        away_bench_evt = next((r for r in events_rows if r.type == 'away_bench'), None)
        subs_evt = next((r for r in events_rows if r.type == 'substitutions'), None)

        import json
        exact_lineup_found = False
        if home_lineup_evt and home_lineup_evt.details:
            try:
                match_details["home_lineup"] = json.loads(home_lineup_evt.details)
                if home_lineup_evt.player:
                    match_details["home_formation"] = home_lineup_evt.player
                exact_lineup_found = True
            except Exception:
                pass

        if away_lineup_evt and away_lineup_evt.details:
            try:
                match_details["away_lineup"] = json.loads(away_lineup_evt.details)
                if away_lineup_evt.player:
                    match_details["away_formation"] = away_lineup_evt.player
            except Exception:
                pass

        if home_bench_evt and home_bench_evt.details:
            try:
                match_details["home_bench"] = json.loads(home_bench_evt.details)
            except Exception:
                pass

        if away_bench_evt and away_bench_evt.details:
            try:
                match_details["away_bench"] = json.loads(away_bench_evt.details)
            except Exception:
                pass

        if subs_evt and subs_evt.details:
            try:
                match_details["substitutions"] = json.loads(subs_evt.details)
            except Exception:
                pass

        # Parse substitutions from events if not explicitly stored
        if not match_details["substitutions"]:
            subs_list = []
            for e in match_details["events"]:
                det = e.get("details", "")
                if e.get("type") == "substitution" or " replaced by " in det or " comes on for " in det:
                    p_in = e.get("player", "")
                    p_out = ""
                    if " replaced by " in det:
                        parts = det.split(" replaced by ")
                        p_out = parts[0].strip()
                        p_in = parts[1].split("(")[0].strip()
                    elif " comes on for " in det:
                        parts = det.split(" comes on for ")
                        p_in = parts[0].replace("Substitution:", "").strip()
                        p_out = parts[1].split("(")[0].strip()
                    
                    if p_in and p_out:
                        subs_list.append({
                            "minute": e.get("minute", 0),
                            "team": e.get("team", "home"),
                            "player_out": p_out,
                            "player_in": p_in,
                            "reason": "injury" if "injury" in det.lower() else "tactical"
                        })
            match_details["substitutions"] = subs_list

        # Fallback if no stored exact lineup/bench exists for this match
        if not exact_lineup_found or not match_details["home_lineup"] or not match_details["away_lineup"]:
            from database.models import Player
            home_players_db = db.query(Player).filter(Player.team_id == m.home_team_id).all()
            away_players_db = db.query(Player).filter(Player.team_id == m.away_team_id).all()

            def build_smart_lineup_and_bench(players_db, team_name, is_home=True):
                target_team_code = "home" if is_home else "away"
                team_events = [e for e in match_details["events"] if e.get("team") == target_team_code or team_name.lower() in e.get("details", "").lower()]
                team_subs = [s for s in match_details["substitutions"] if s.get("team") == target_team_code]

                subbed_in_names = {s["player_in"].lower().strip() for s in team_subs}
                subbed_out_names = {s["player_out"].lower().strip() for s in team_subs}

                # Starters mentioned in events: scorers, carded, assisters, subbed_out
                starter_names = set(subbed_out_names)
                for e in team_events:
                    p_name = e.get("player", "").strip().lower()
                    if p_name and p_name not in subbed_in_names:
                        starter_names.add(p_name)
                    det = e.get("details", "")
                    if "Goal!" in det:
                        for p in players_db:
                            if p.name.lower() in det.lower() and p.name.lower() not in subbed_in_names:
                                starter_names.add(p.name.lower())

                starters = []
                bench = []
                remaining = []

                for p in players_db:
                    p_lower = p.name.lower().strip()
                    if p_lower in starter_names and len(starters) < 11:
                        starters.append(p)
                    elif p_lower in subbed_in_names and len(bench) < 7:
                        bench.append(p)
                    else:
                        remaining.append(p)

                # Fill starters up to 11
                while len(starters) < 11 and remaining:
                    starters.append(remaining.pop(0))
                # Fill bench up to 7
                while len(bench) < 7 and remaining:
                    bench.append(remaining.pop(0))

                return starters, bench

            h_starters, h_bench = build_smart_lineup_and_bench(home_players_db, match_details["home_team_name"], is_home=True)
            a_starters, a_bench = build_smart_lineup_and_bench(away_players_db, match_details["away_team_name"], is_home=False)

            def format_player_list(players_list, default_role="STARTER"):
                result = []
                for idx, p in enumerate(players_list):
                    num = 1 if p.position == "GK" and default_role == "STARTER" and idx == 0 else (idx + 1 if default_role == "STARTER" else idx + 12)
                    result.append({
                        "player_id": p.player_id,
                        "name": p.name,
                        "position": p.position,
                        "number": num,
                        "potential": p.potential,
                        "wage": p.wage,
                        "squad_role": default_role
                    })
                return result

            if not match_details["home_lineup"]:
                match_details["home_lineup"] = format_player_list(h_starters, "STARTER")
            if not match_details["home_bench"]:
                match_details["home_bench"] = format_player_list(h_bench, "BENCH")
            if not match_details["away_lineup"]:
                match_details["away_lineup"] = format_player_list(a_starters, "STARTER")
            if not match_details["away_bench"]:
                match_details["away_bench"] = format_player_list(a_bench, "BENCH")

        # Check for replay video file with run-scoped priority
        from config import RECORDINGS_DIR
        run_id = getattr(m, "simulation_run_id", None)
        stored_url = getattr(m, "video_url", None)

        match_details["simulation_run_id"] = run_id
        resolved_video = None

        if stored_url:
            clean_rel = stored_url.replace("\\", "/").replace("/recordings/", "").lstrip("/")
            try:
                candidate = (RECORDINGS_DIR / clean_rel).resolve()
                candidate.relative_to(RECORDINGS_DIR.resolve())
                if candidate.exists():
                    resolved_video = f"/recordings/{candidate.relative_to(RECORDINGS_DIR.resolve()).as_posix()}"
            except ValueError:
                logger.warning("Ignored recording path outside artifact root for match %s", m.match_id)

        if not resolved_video:
            clean_str = str(match_id).strip()
            raw_sub = clean_str[6:] if clean_str.startswith("match_") else clean_str
            candidate_names = [
                f"{clean_str}_3d.mp4",
                f"{clean_str}_2d.mp4",
                f"{clean_str}.mp4",
                f"match_{clean_str}.mp4",
                f"match_match_{clean_str}.mp4",
                f"{raw_sub}.mp4",
                f"match_{raw_sub}.mp4",
                f"match_{raw_sub}_3d.mp4",
                f"match_{raw_sub}_2d.mp4",
                f"match_match_{raw_sub}.mp4",
                f"match_{m.match_id}.mp4",
                f"match_{m.match_id}_3d.mp4",
                f"match_{m.match_id}_2d.mp4",
                f"match_match_{m.match_id}.mp4",
                f"match_{m.match_number}.mp4",
                f"match_match_{m.match_number}.mp4",
            ]
            sy = match_details.get("season_year")
            hid = match_details.get("home_team_id")
            aid = match_details.get("away_team_id")
            if sy and hid and aid:
                candidate_names.extend([
                    f"match_{sy}_{hid}_{aid}.mp4",
                    f"match_match_{sy}_{hid}_{aid}.mp4",
                    f"match_{hid}_{aid}.mp4",
                ])
            tf = getattr(m, "trace_file", None)
            if tf and str(tf).endswith(".mp4"):
                candidate_names.insert(0, os.path.basename(str(tf)))

            unique_candidates = []
            for c in candidate_names:
                if c and c not in unique_candidates:
                    unique_candidates.append(c)

            # Check in specific run_id directory if known
            if run_id:
                for c in unique_candidates:
                    p = RECORDINGS_DIR / run_id / c
                    if p.exists() and p.stat().st_size > 0:
                        resolved_video = f"/recordings/{run_id}/{c}"
                        break

            # Check in root RECORDINGS_DIR
            if not resolved_video:
                for c in unique_candidates:
                    p = RECORDINGS_DIR / c
                    if p.exists() and p.stat().st_size > 0:
                        resolved_video = f"/recordings/{c}"
                        break

            # Check in any run_* directory
            if not resolved_video:
                for run_dir in RECORDINGS_DIR.glob("run_*"):
                    if run_dir.is_dir():
                        for c in unique_candidates:
                            p = run_dir / c
                            if p.exists() and p.stat().st_size > 0:
                                resolved_video = f"/recordings/{run_dir.name}/{c}"
                                break
                        if resolved_video:
                            break

        if resolved_video and getattr(m, "video_url", None) != resolved_video:
            try:
                m.video_url = resolved_video
                db.commit()
            except Exception:
                pass

        match_details["video_url"] = resolved_video
        return match_details
    except Exception as e:
        logger.error(f"Database error fetching match details: {e}")
        return None
    finally:
        db.close()

