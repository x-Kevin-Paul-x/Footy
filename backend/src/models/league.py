import os
import json
from datetime import datetime
import random
from models.match import Match
from models.team import Team
from models.manager import Manager
from models.coach import Coach
from models.transfer import TransferMarket
from database.match_db import get_matches_for_season
from database.league_db import create_league, get_league, update_league, delete_league
from database.player_db import update_player
from database.team_db import update_team

class League:
    def __init__(self, name, num_teams=20):
        self.name = name
        self.teams = []  # Initialize empty, will be populated by main.py
        self.matches = []
        self.standings = {}
        # Relative to backend/src/models/league.py
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.match_reports_dir = os.path.join(BASE_DIR, "..", "..", "reports", "match_reports")
        self.historical_standings = []
        self.season_year = datetime.now().year
        self.schedule = []  # Store the match schedule
        
        # Database attributes
        self.league_id = None
        
        # Create directory for match reports
        self._init_season()
        os.makedirs(self.match_reports_dir, exist_ok=True)
        
        # Initialize TransferMarket for the league instance
        self.transfer_market = TransferMarket(log_path=f"season_{self.season_year}_transfers.txt")

    def save_to_database(self):
        """Save league to database"""
        if self.league_id is None:
            # Create new league
            self.league_id = create_league(
                name=self.name,
                season_year=self.season_year,
                num_teams=len(self.teams)
            )
        else:
            # Update existing league
            update_league(
                league_id=self.league_id,
                name=self.name,
                season_year=self.season_year,
                num_teams=len(self.teams)
            )
        return self.league_id

    @classmethod
    def load_from_database(cls, league_id):
        """Load league from database by ID"""
        data = get_league(league_id)
        if not data:
            return None
            
        league = cls(
            name=data["name"],
            num_teams=data["num_teams"]
        )
        league.league_id = data["league_id"]
        league.season_year = data["season_year"]
        return league

    def generate_schedule(self):
        """Create a proper double round-robin schedule"""
        fixtures = []
        teams = self.teams
        n = len(teams)
        
        # Create home/away matches for each unique pair
        for i in range(n):
            for j in range(n):
                if i != j:
                    fixtures.append((teams[i], teams[j]))
        
        # Randomize match order to create realistic schedule
        random.shuffle(fixtures)
        self.schedule = fixtures
        self.matches = fixtures  # Keep both for compatibility

    def derive_match_seed(self, home_team, away_team) -> int:
        """Canonical seed derivation function guaranteeing identical seeds across execution backends."""
        import hashlib
        key = f"{self.name}_{self.season_year}_{home_team.team_id}_{away_team.team_id}"
        return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:4], "little")

    def select_team_lineup(self, team, opponent=None):
        """Canonical lineup selection function used uniformly before backend dispatch."""
        if team.manager:
            lineup, positions = team.manager.select_lineup(team.players, opponent=opponent)
        else:
            lineup, positions = self._select_default_lineup(team)
        return lineup, positions

    def _select_default_lineup(self, team):
        available_players = [p for p in team.players if getattr(p, "is_available_for_selection", lambda: True)()]
        goalkeepers = [p for p in available_players if p.position == "GK"]
        defenders = [p for p in available_players if p.position in ["CB", "LB", "RB", "SW", "LWB", "RWB"]]
        midfielders = [p for p in available_players if p.position in ["CM", "CDM", "CAM", "LM", "RM", "DM"]]
        forwards = [p for p in available_players if p.position in ["ST", "CF", "SS", "LW", "RW"]]
        for group in [goalkeepers, defenders, midfielders, forwards]:
            group.sort(key=lambda p: (p.get_overall_rating() if hasattr(p, "get_overall_rating") else getattr(p, "potential", 70)) * (p.stats.get("fitness", 100)/100 if hasattr(p, "stats") and isinstance(p.stats, dict) else 1.0), reverse=True)
        lineup = []
        positions = []
        if goalkeepers:
            lineup.append(goalkeepers[0])
            positions.append("GK")
        lineup.extend(defenders[:4])
        positions.extend(["CB", "CB", "LB", "RB"][:len(defenders[:4])])
        lineup.extend(midfielders[:4])
        positions.extend(["CM", "CM", "LM", "RM"][:len(midfielders[:4])])
        lineup.extend(forwards[:2])
        positions.extend(["ST", "ST"][:len(forwards[:2])])
        return lineup[:11], positions[:11]

    def prepare_match(self, home_team, away_team, match_id=None, seed_val=None):
        """Canonical match-preparation path returning a typed PreparedMatch dataclass."""
        from models.match import PreparedMatch
        from logic.footy_grf_adapter import FootyGRFAdapter

        m_id = match_id or f"match_{self.season_year}_{home_team.team_id}_{away_team.team_id}"
        s_val = seed_val if seed_val is not None else self.derive_match_seed(home_team, away_team)

        h_lineup, h_pos = self.select_team_lineup(home_team, opponent=away_team)
        a_lineup, a_pos = self.select_team_lineup(away_team, opponent=home_team)

        def select_matchday_bench(team, lineup, max_bench=7):
            available = [p for p in team.players if p not in lineup and getattr(p, "is_available_for_selection", lambda: True)()]
            available.sort(key=lambda p: (p.get_overall_rating() if hasattr(p, "get_overall_rating") and callable(p.get_overall_rating) else getattr(p, "potential", 70)), reverse=True)
            return available[:max_bench]

        h_bench = select_matchday_bench(home_team, h_lineup)
        a_bench = select_matchday_bench(away_team, a_lineup)

        h_tactics = FootyGRFAdapter.build_team_tactics(home_team, lineup=h_lineup, positions=h_pos)
        a_tactics = FootyGRFAdapter.build_team_tactics(away_team, lineup=a_lineup, positions=a_pos)

        h_profiles = [p.to_dict() for p in h_tactics.roster]
        a_profiles = [p.to_dict() for p in a_tactics.roster]

        return PreparedMatch(
            match_id=m_id,
            seed_val=s_val,
            home_team=home_team,
            away_team=away_team,
            home_lineup=h_lineup,
            away_lineup=a_lineup,
            home_positions=h_pos,
            away_positions=a_pos,
            home_bench=h_bench,
            away_bench=a_bench,
            home_formation=h_tactics.formation,
            away_formation=a_tactics.formation,
            home_tactics=h_tactics,
            away_tactics=a_tactics,
            home_profiles=h_profiles,
            away_profiles=a_profiles,
        )

    def play_match(self, home_team, away_team):
        """Play a single match between two teams with league-level emergency squad intervention and manager learning."""
        min_players = 11
        pre_match_penalty = -20.0
        youth_promotion_reward = 5.0
        forfeit_penalty = -150.0

        for team in [home_team, away_team]:
            # Generate more youth players weekly to keep academy full
            team.generate_youth_players_weekly(count=3)

            # Check if team has enough players
            healthy_players = [p for p in team.players if not getattr(p, "is_injured", False) and p.stats.get("fitness", 100) > 30]
            if len(healthy_players) < min_players:
                # Penalize manager for not having enough players
                if team.manager:
                    team.manager.learn_from_match({
                        "winner": False,
                        "draw": False,
                        "goals_for": 0,
                        "goals_against": 0,
                        "pre_match_penalty": True,
                        "reward_override": pre_match_penalty
                    })
                # Promote youth players and give a small reward
                promoted = 0
                youth_to_promote = sorted(team.youth_academy, key=lambda p: p.potential, reverse=True)
                for player in youth_to_promote:
                    if len(healthy_players) >= min_players:
                        break
                    team.promote_youth_player(player)
                    promoted += 1
                    healthy_players.append(player)
                if promoted > 0 and team.manager:
                    team.manager.learn_from_match({
                        "winner": False,
                        "draw": False,
                        "goals_for": 0,
                        "goals_against": 0,
                        "youth_promotion": True,
                        "reward_override": youth_promotion_reward
                    })
                # If still not enough, system intervenes and generates youth
                while len(healthy_players) < min_players:
                    player = team.generate_youth_player()
                    team.promote_youth_player(player)
                    healthy_players.append(player)
                # If after all this, still not enough, forfeit with harsher penalty
                if len(healthy_players) < min_players and team.manager:
                    team.manager.learn_from_match({
                        "winner": False,
                        "draw": False,
                        "goals_for": 0,
                        "goals_against": 0,
                        "forfeit": True,
                        "reward_override": forfeit_penalty
                    })

            team.check_and_reinforce_squad(self.transfer_market)
            self._ensure_minimum_squad(team, min_players=min_players)

        # Weekly training and development for both teams
        for team in [home_team, away_team]:
            # Calculate team performance multiplier
            team_perf = self.standings.get(team.name, {}).get("points", 0)
            max_points = max([self.standings[t.name]["points"] for t in self.teams if t.name in self.standings], default=1)
            perf_multiplier = 1.0 + 0.5 * (team_perf / max_points) if max_points > 0 else 1.0
            # All training handled by coaches only
            self._weekly_team_training(team)

        # Play the match using canonical PreparedMatch
        prepared = self.prepare_match(home_team, away_team)
        match = Match(home_team, away_team, prepared_match=prepared, seed_val=prepared.seed_val)
        try:
            result = match.play_match(match_id=prepared.match_id, seed_val=prepared.seed_val)
            # Post-match player updates: suspensions and injury recovery
            for team in [home_team, away_team]:
                for player in team.players:
                    if getattr(player, "suspended_matches", 0) > 0:
                        player.serve_suspension(1)
                    if getattr(player, "is_injured", False):
                        player.recover_from_injury(7)
            self.update_standings(home_team, away_team, result)
            result['home_team_id'] = home_team.team_id
            result['away_team_id'] = away_team.team_id
            return result
        except ValueError as e:
            # Log forfeit due to insufficient players
            forfeit_result = {
                "score": [0, 0],
                "possession": [0, 0],
                "shots": [0, 0],
                "shots_on_target": [0, 0],
                "weather": getattr(match, "weather", "N/A"),
                "events": [str(e)],
                "home_team_id": home_team.team_id,
                "away_team_id": away_team.team_id
            }
            print(f"Match forfeited: {e}")
            self.update_standings(home_team, away_team, forfeit_result)
            # Give managers a strong negative reward for forfeiting
            for team in [home_team, away_team]:
                if team.manager:
                    team.manager.learn_from_match({
                        "winner": False,
                        "draw": False,
                        "goals_for": 0,
                        "goals_against": 0,
                        "forfeit": True,
                        "reward_override": forfeit_penalty
                    })
    def play_matchday(self, fixtures_batch):
        """
        Play a batch of matches (e.g. 10 fixtures of a matchday) concurrently
        using GRFBatchRunner with GPU batching when GRF is enabled.
        """
        from config import ENGINE_MODE
        if ENGINE_MODE in ["GRF", "AUTO"]:
            try:
                from logic.grf_batch_runner import GRFBatchRunner
                runner = GRFBatchRunner()
                if runner.is_available():
                    # Pre-match preparation for all fixtures
                    min_players = 11
                    for home_team, away_team in fixtures_batch:
                        for team in [home_team, away_team]:
                            team.generate_youth_players_weekly(count=3)
                            team.check_and_reinforce_squad(self.transfer_market)
                            self._ensure_minimum_squad(team, min_players=min_players)
                            self._weekly_team_training(team)

                    prepared_matches = [self.prepare_match(home_team, away_team) for home_team, away_team in fixtures_batch]
                    fixtures_payload = [p.to_fixture_dict() for p in prepared_matches]
                    batch_results = runner.run_matchday(fixtures_payload)
                    results = []
                    for idx, res in enumerate(batch_results):
                        home_team, away_team = fixtures_batch[idx]
                        prep = prepared_matches[idx]
                        for team in [home_team, away_team]:
                            for player in team.players:
                                if getattr(player, "suspended_matches", 0) > 0:
                                    player.serve_suspension(1)
                                if getattr(player, "is_injured", False):
                                    player.recover_from_injury(7)
                        self.update_standings(home_team, away_team, res)
                        res['home_team_id'] = home_team.team_id
                        res['away_team_id'] = away_team.team_id
                        res['home_lineup'] = [{"name": p.name, "position": getattr(p, "position", "ST")} for p in prep.home_lineup]
                        res['away_lineup'] = [{"name": p.name, "position": getattr(p, "position", "ST")} for p in prep.away_lineup]
                        results.append(res)
                    return results
            except Exception as e:
                import logging
                from config import ENGINE_MODE
                if ENGINE_MODE == "GRF":
                    logging.getLogger(__name__).error(f"Batch GRF execution error under strict GRF mode: {e}")
                    raise RuntimeError(f"Batch GRF execution failed under strict GRF mode: {e}") from e
                logging.getLogger(__name__).warning(f"Batch GRF execution error: {e}. Falling back to sequential heuristic in AUTO mode.")

        # Fallback to sequential play_match
        return [self.play_match(home, away) for home, away in fixtures_batch]

    def play_matchdays_concurrent(self, matchdays_batches, max_workers=2):
        """
        Play multiple matchdays sequentially in strict chronological order,
        parallelizing only independent fixtures belonging to the SAME matchday.
        """
        from config import ENGINE_MODE
        if ENGINE_MODE in ["GRF", "AUTO"]:
            try:
                from logic.grf_batch_runner import GRFBatchRunner
                runner = GRFBatchRunner()
                if runner.is_available():
                    all_matchdays_results = []
                    min_players = 11

                    for fixtures_batch in matchdays_batches:
                        # Pre-match preparation strictly for THIS matchday
                        for home_team, away_team in fixtures_batch:
                            for team in [home_team, away_team]:
                                team.generate_youth_players_weekly(count=3)
                                team.check_and_reinforce_squad(self.transfer_market)
                                self._ensure_minimum_squad(team, min_players=min_players)
                                self._weekly_team_training(team)

                        prepared_matches = [self.prepare_match(home_team, away_team) for home_team, away_team in fixtures_batch]
                        fixtures_payload = [p.to_fixture_dict() for p in prepared_matches]

                        batch_results = runner.run_matchday(fixtures_payload)
                        results = []
                        for idx, res in enumerate(batch_results):
                            home_team, away_team = fixtures_batch[idx]
                            prep = prepared_matches[idx]
                            for team in [home_team, away_team]:
                                for player in team.players:
                                    if getattr(player, "suspended_matches", 0) > 0:
                                        player.serve_suspension(1)
                                    if getattr(player, "is_injured", False):
                                        player.recover_from_injury(7)
                            self.update_standings(home_team, away_team, res)
                            res['home_team_id'] = home_team.team_id
                            res['away_team_id'] = away_team.team_id
                            res['home_lineup'] = [{"name": p.name, "position": getattr(p, "position", "ST")} for p in prep.home_lineup]
                            res['away_lineup'] = [{"name": p.name, "position": getattr(p, "position", "ST")} for p in prep.away_lineup]
                            results.append(res)
                        all_matchdays_results.append(results)

                    return all_matchdays_results
            except Exception as e:
                import logging
                from config import ENGINE_MODE
                if ENGINE_MODE == "GRF":
                    logging.getLogger(__name__).error(f"Concurrent GRF execution error under strict GRF mode: {e}")
                    raise RuntimeError(f"Concurrent GRF execution failed under strict GRF mode: {e}") from e
                logging.getLogger(__name__).warning(f"Concurrent GRF execution error: {e}. Falling back to heuristic in AUTO mode.")

        return [self.play_matchday(batch) for batch in matchdays_batches]

    def play_season(self):
        """Play all matches in the season and close the transfer log."""
        from datetime import datetime, timedelta
        match_day = 1

        # Initialize the transfer log for the season
        REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reports")
        log_path = os.path.join(REPORTS_DIR, "transfer_logs", f"season_{self.season_year}_transfers.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"Transfer Activity for Season {self.season_year}\n")
            f.write("=" * 80 + "\n\n")

        # Schedule: assume matches_per_week = len(self.teams) // 2
        season_start = datetime(self.season_year, 8, 1)
        matches_per_week = max(1, len(self.teams) // 2)
        for idx, (home, away) in enumerate(self.schedule):
            matchday = idx // matches_per_week
            scheduled_date = season_start + timedelta(days=7 * matchday)
            result = self.play_match(home, away)
            result["date"] = scheduled_date.isoformat()
            self.save_match_report_simple(home, away, result, idx+1)

    def save_match_report_simple(self, home_team, away_team, result, match_number):
        """Save simplified match report"""
        report = {
            "match_number": match_number,
            "date": datetime.now().isoformat(),
            "season_year": self.season_year,
            "home_team": home_team.name,
            "away_team": away_team.name,
            "score": result["score"],
            "possession": result.get("possession", [50, 50]),
            "shots": result.get("shots", [0, 0]),
            "shots_on_target": result.get("shots_on_target", [0, 0]),
            "weather": result.get("weather", "N/A"),
            "events": len(result.get("events", []))
        }
        
        filename = f"{self.season_year}_Match_{match_number:04d}.json"
        path = os.path.join(self.match_reports_dir, filename)
        
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)

    def _ensure_minimum_squad(self, team, min_players=11):
        """Ensure the team has at least min_players healthy/fit players by promoting youth or generating bad youth."""
        def healthy_players():
            return [p for p in team.players if not getattr(p, "is_injured", False) and p.stats.get("fitness", 100) > 30]

        while len(healthy_players()) < min_players:
            # Prevent exceeding squad size limit
            if len(team.players) >= 40:
                break
            # Try to promote the oldest youth player
            if team.youth_academy:
                oldest = max(team.youth_academy, key=lambda p: p.age)
                team.promote_youth_player(oldest)
                oldest.stats["fitness"] = 100
                oldest.is_injured = False
            else:
                # Generate a bad youth player (potential 50-60, low ability)
                from models.player import FootballPlayer
                age = random.randint(15, 18)
                potential = random.randint(50, 60)
                bad_youth = FootballPlayer.create_player(age=age, potential=potential)
                bad_youth.squad_role = "YOUTH"
                bad_youth.stats["fitness"] = 100
                bad_youth.is_injured = False
                team.youth_academy.append(bad_youth)
                team.promote_youth_player(bad_youth)

    def save_match_report(self, match, result, match_number):
        """Save match details to JSON file"""
        report = {
            "match_number": match_number,
            "date": datetime.now().isoformat(),
            "season_year": self.season_year,
            "home_team": match.home_team.name,
            "away_team": match.away_team.name,
            "score": result["score"],
            "possession": result.get("possession", [50, 50]),
            "shots": result.get("shots", {"total": [0, 0], "on_target": [0, 0]}),
            "weather": getattr(match, "weather", "N/A"),
            "intensity": getattr(match, "intensity", 1.0)
        }
        
        filename = f"{datetime.now().year}_Match_{match_number:04d}.json"
        path = os.path.join(self.match_reports_dir, filename)
        
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)

    def update_standings(self, home, away, result):
        """Update league standings based on match result"""
        # Initialize team standings if not exists
        for team in [home, away]:
            if team.name not in self.standings:
                self.standings[team.name] = {
                    "points": 0,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "gf": 0,
                    "ga": 0,
                    "gd": 0,
                    "recent_form": []
                }
        
        # Update match stats
        home_goals = result["score"][0]
        away_goals = result["score"][1]
        
        # Home team
        self.standings[home.name]["played"] += 1
        self.standings[home.name]["gf"] += home_goals
        self.standings[home.name]["ga"] += away_goals
        self.standings[home.name]["gd"] = self.standings[home.name]["gf"] - self.standings[home.name]["ga"]
        
        # Away team
        self.standings[away.name]["played"] += 1
        self.standings[away.name]["gf"] += away_goals
        self.standings[away.name]["ga"] += home_goals
        self.standings[away.name]["gd"] = self.standings[away.name]["gf"] - self.standings[away.name]["ga"]
        
        # Update points and form
        if home_goals > away_goals:
            self.standings[home.name]["won"] += 1
            self.standings[home.name]["points"] += 3
            self.standings[away.name]["lost"] += 1
            # Update form
            self.standings[home.name]["recent_form"].append("W")
            self.standings[away.name]["recent_form"].append("L")
        elif home_goals < away_goals:
            self.standings[away.name]["won"] += 1
            self.standings[away.name]["points"] += 3
            self.standings[home.name]["lost"] += 1
            # Update form
            self.standings[away.name]["recent_form"].append("W")
            self.standings[home.name]["recent_form"].append("L")
        else:
            self.standings[home.name]["drawn"] += 1
            self.standings[home.name]["points"] += 1
            self.standings[away.name]["drawn"] += 1
            self.standings[away.name]["points"] += 1
            # Update form
            self.standings[home.name]["recent_form"].append("D")
            self.standings[away.name]["recent_form"].append("D")
        
        # Keep only last 5 form results
        for team in [home, away]:
            if len(self.standings[team.name]["recent_form"]) > 5:
                self.standings[team.name]["recent_form"] = self.standings[team.name]["recent_form"][-5:]

    def get_league_table(self):
        """Generate sorted league table"""
        sorted_table = sorted(self.standings.items(),
                            key=lambda x: (-x[1]['points'], -x[1]['gd'], -x[1]['gf']))
        return sorted_table

    def get_final_table(self):
        """Get final league table (alias for compatibility)"""
        return self.get_league_table()

    def get_best_manager(self):
        """Find manager with best performance metrics and return as a dictionary."""
        if not self.standings:
            return {
                "name": "N/A",
                "experience": 0,
                "formation": "N/A",
                "transfer_success_rate": 0.0,
                "market_trends": {}
            }

        champions_data = max(self.standings.items(), key=lambda x: x[1]['points'])
        champion_team_name = champions_data[0]
        champion_team = next((t for t in self.teams if t.name == champion_team_name), None)

        if champion_team and champion_team.manager:
            manager = champion_team.manager
            manager_stats = manager.get_stats()
            return {
                "name": manager.name,
                "experience": manager.experience_level,
                "formation": manager.formation,
                "transfer_success_rate": manager_stats.get("transfer_success_rate", 0.0),
                "market_trends": manager.analyze_market_trends() 
            }
        
        # Fallback if champion manager not found
        best_fallback_manager = None
        highest_win_rate = -1

        for team_obj in self.teams:
            if team_obj.manager:
                manager = team_obj.manager
                if manager.matches_played > 0:
                    win_rate = manager.wins / manager.matches_played
                    if win_rate > highest_win_rate:
                        highest_win_rate = win_rate
                        best_fallback_manager = manager
                elif best_fallback_manager is None:
                    best_fallback_manager = manager
        
        if best_fallback_manager:
            manager_stats = best_fallback_manager.get_stats()
            return {
                "name": best_fallback_manager.name,
                "experience": best_fallback_manager.experience_level,
                "formation": best_fallback_manager.formation,
                "transfer_success_rate": manager_stats.get("transfer_success_rate", 0.0),
                "market_trends": best_fallback_manager.analyze_market_trends()
            }
        return {"name": "N/A", "experience": 0, "formation": "N/A", "transfer_success_rate": 0.0, "market_trends": {}}

    def get_best_players(self, num=11):
        """Get best players in the league based on overall rating"""
        all_players = []
        for team in self.teams:
            all_players.extend(team.players)

        # Sort players by overall rating
        all_players.sort(key=lambda p: p.get_overall_rating(), reverse=True)

        # Get top players and their details
        best_players_data = []
        for player_obj in all_players[:num]:
            player_info = player_obj.get_player_info(detail_level="full")
            player_info["value"] = self.transfer_market.calculate_player_value(player_obj)
            player_info["team"] = player_obj.team if player_obj.team else "N/A"
            best_players_data.append(player_info)

        return best_players_data

    def increment_season(self):
        """Advance to new season and age all players."""
        self.season_year += 1

        # Process contract renewals and expiries FIRST (before aging causes retirement)
        # This prevents players from being removed before contracts can be renewed
        self._process_all_contracts()

        # Age all players and retire old ones
        retirement_age = 36
        for team in self.teams:
            # Age main squad players
            players_to_remove = []
            for player in team.players:
                player.age += 1
                # Reset fitness and injury for new season
                player.stats["fitness"] = min(100, player.stats.get("fitness", 100) + 30)
                player.is_injured = False
                player.recovery_time = 0
                # Reset cards for new season
                player.stats["yellow_cards"] = 0
                player.stats["red_cards"] = 0
                
                if player.age >= retirement_age:
                    players_to_remove.append(player)
            for player in players_to_remove:
                team.remove_player(player)

            # Age youth academy players
            youth_to_remove = []
            for player in team.youth_academy:
                player.age += 1
                # Ensure youth are match-ready when promoted
                player.stats["fitness"] = 100
                player.is_injured = False
                if player.age >= retirement_age:
                    youth_to_remove.append(player)
            for player in youth_to_remove:
                team.youth_academy.remove(player)

            # Generate 3-5 new youth players per season (increased for sustainability)
            for _ in range(random.randint(3, 5)):
                team.generate_youth_player()
            
            # Ensure minimum squad size of 18 players
            while len(team.players) < 18:
                # First try to promote from youth academy
                if team.youth_academy:
                    best_youth = max(team.youth_academy, key=lambda p: p.potential)
                    team.promote_youth_player(best_youth)
                    best_youth.stats["fitness"] = 100
                    best_youth.is_injured = False
                else:
                    # Generate emergency youth player
                    new_player = team.generate_youth_player()
                    team.promote_youth_player(new_player)
                    new_player.stats["fitness"] = 100
                    new_player.is_injured = False
            
            # Let manager decide additional youth promotions
            if team.manager:
                team.manager.decide_promotions()

        # Simulate youth tournament and apply growth
        self.simulate_youth_tournament()

        self._init_season()
        print(f"Advanced to season {self.season_year}")

    def _process_all_contracts(self):
        """Process contract renewals and expirations for all teams."""
        for team in self.teams:
            players_to_keep = []
            for player in team.players[:]:  # Copy list to avoid modification during iteration
                player.contract_length -= 1
                
                # Renew contracts for valuable players before they expire
                if player.contract_length <= 1:
                    if self._should_auto_renew(player, team):
                        player.contract_length = random.randint(2, 4)  # 2-4 year extension
                        player.wage = player.wage * random.uniform(1.05, 1.15)  # Small wage increase
                
                # Keep player if contract is valid
                if player.contract_length > 0:
                    players_to_keep.append(player)
                else:
                    # Contract expired - player leaves
                    team.remove_player(player)
                    player.team = None
    
    def _should_auto_renew(self, player, team):
        """Determine if a player's contract should be automatically renewed."""
        # Always renew if squad is small
        if len(team.players) <= 18:
            return True
        
        # High-rated players
        if player.get_overall_rating() > 75:
            return True
        
        # Young players with good potential
        if player.age < 26 and player.potential > 70:
            return True
        
        # Key starters
        if player.squad_role == "STARTER":
            return True
        
        # Don't renew old, low-quality players if squad is large
        if player.age > 32 and player.get_overall_rating() < 70:
            return len(team.players) <= 22
        
        # Default: renew to maintain squad
        return len(team.players) <= 22

    def simulate_youth_tournament(self):
        """Simulate a youth tournament for all teams' youth academies."""
        # Each team fields up to 5 youth players
        youth_teams = []
        for team in self.teams:
            youth_team = team.youth_academy[:5] if len(team.youth_academy) >= 5 else team.youth_academy[:]
            youth_teams.append((team, youth_team))

        # Simple round-robin
        results = {team.name: 0 for team, _ in youth_teams}
        for i, (team_a, players_a) in enumerate(youth_teams):
            for j, (team_b, players_b) in enumerate(youth_teams):
                if i >= j:
                    continue
                outcome = random.choices(["A", "B", "D"], weights=[0.4, 0.4, 0.2])[0]
                if outcome == "A":
                    results[team_a.name] += 3
                    self._apply_youth_growth(players_a, win=True)
                    self._apply_youth_growth(players_b, win=False)
                elif outcome == "B":
                    results[team_b.name] += 3
                    self._apply_youth_growth(players_b, win=True)
                    self._apply_youth_growth(players_a, win=False)
                else:
                    results[team_a.name] += 1
                    results[team_b.name] += 1
                    self._apply_youth_growth(players_a, win=False, draw=True)
                    self._apply_youth_growth(players_b, win=False, draw=True)

    def _apply_youth_growth(self, players, win=False, draw=False):
        """Apply attribute growth to youth players based on match result."""
        for player in players:
            if win:
                growth = 0.7
            elif draw:
                growth = 0.4
            else:
                growth = 0.2
            # Apply growth to all attributes
            for attr_type in player.attributes:
                for sub_attr in player.attributes[attr_type]:
                    player.attributes[attr_type][sub_attr] = min(
                        95.0, player.attributes[attr_type][sub_attr] + growth + random.uniform(0, 0.3)
                    )

    def _get_position_group(self, position):
        """Convert specific position to position group - fixed method"""
        if position == "GK":
            return "GK"
        elif position in ["CB", "LB", "RB", "LWB", "RWB", "SW"]:
            return "DEF"
        elif position in ["CM", "CDM", "CAM", "LM", "RM", "DM"]:
            return "MID"
        else:
            return "FWD"

    def _calculate_need_satisfaction(self, team: Team, player) -> float:
        """Calculate how well a player satisfies team needs."""
        squad_needs = team.get_squad_needs()
        position_group = self._get_position_group(player.position)
        
        # Get current and ideal counts for the position
        position_analysis = squad_needs.get("position_analysis", {})
        if position_group not in position_analysis:
            return 0.0
            
        current_count = position_analysis[position_group]["current"]
        ideal_count = position_analysis[position_group]["ideal"]
        
        if ideal_count == 0:
            return 0.0
            
        # Calculate need satisfaction (0.0 to 1.0)
        if current_count < ideal_count:
            return 1.0  # Fills a needed position
        else:
            return max(0.0, 1.0 - ((current_count - ideal_count) / ideal_count))

    def _weekly_team_training(self, team):
        """Handle weekly training and development for a team."""
        # Organize players by position groups
        position_groups = {
            "GK": [],
            "DEF": [],
            "MID": [],
            "FWD": []
        }
        
        for player in team.players:
            if player.position == "GK":
                position_groups["GK"].append(player)
            elif player.position in ["CB", "LB", "RB", "LWB", "RWB", "SW"]:
                position_groups["DEF"].append(player)
            elif player.position in ["CM", "CDM", "CAM", "LM", "RM", "DM"]:
                position_groups["MID"].append(player)
            else:
                position_groups["FWD"].append(player)

        # Train all players with coach specialization
        for coach in team.coaches:
            # Determine coach's best position group
            coach_specialty = "MID"  # Default
            if hasattr(coach, 'specialty'):
                if "GK" in coach.specialty:
                    coach_specialty = "GK"
                elif any(pos in coach.specialty for pos in ["CB", "LB", "RB", "LWB", "RWB", "SW"]):
                    coach_specialty = "DEF"
                elif any(pos in coach.specialty for pos in ["ST", "CF", "LW", "RW"]):
                    coach_specialty = "FWD"

            # Train all players with appropriate intensity
            for group, players in position_groups.items():
                for player in players:
                    # If player is too fatigued, do recovery instead of training
                    if player.stats["fitness"] < 60:
                        player.stats["fitness"] = min(100, player.stats["fitness"] + 20)
                        continue

                    # Determine training intensity based on player fitness
                    if player.stats["fitness"] > 80:
                        intensity = "high"
                    elif player.stats["fitness"] > 50:
                        intensity = "medium"
                    else:
                        intensity = "low"
                    
                    # Apply higher coach bonus if player matches coach specialty
                    coach_bonus = getattr(coach, 'experience_level', 5) / 10.0
                    if group == coach_specialty:
                        coach_bonus *= 1.5  # 50% bonus for specialized coaching
                    
                    # Apply training with focus on position-specific attributes
                    focus_area = None
                    if group == "GK":
                        focus_area = "goalkeeping"
                    elif group == "DEF":
                        focus_area = "defending"
                    elif group == "MID":
                        focus_area = "passing"
                    elif group == "FWD":
                        focus_area = "shooting"
                    
                    player.train_player(
                        intensity=intensity,
                        training_days=3,
                        coach_bonus=coach_bonus,
                        focus_area=focus_area
                    )

    def generate_season_report(self):
        """Compile comprehensive season report with detailed team and player information."""
        all_teams_details = []
        for team_obj in self.teams:
            players_data = []
            for player_obj in team_obj.players:
                player_info = player_obj.get_player_info(detail_level="full")
                player_info["market_value"] = self.transfer_market.calculate_player_value(player_obj)
                player_info["squad_role"] = player_obj.squad_role
                # Add current injury status
                player_info["is_injured"] = getattr(player_obj, "is_injured", False)
                player_info["injury_type"] = getattr(player_obj, "injury_type", None)
                player_info["recovery_time"] = getattr(player_obj, "recovery_time", 0)
                player_info["injury_history"] = getattr(player_obj, "injury_history", [])
                # Ensure 'team' field in player_info is just the name string
                player_info["team"] = team_obj.name 
                players_data.append(player_info)
            
            # Process transfer history
            raw_team_transfer_history = team_obj.statistics["transfer_history"]
            processed_team_transfer_history = []
            for item in raw_team_transfer_history:
                if isinstance(item, dict):
                    processed_item = {
                        "type": item.get("type", "unknown"),
                        "player_name": item.get("player_name", "N/A"),
                        "price": item.get("price", 0.0),
                        "success": item.get("success", False),
                        "day_of_window": item.get("day_of_window", None),
                        "message": item.get("message", "")
                    }
                    # Ensure price is a number
                    if not isinstance(processed_item["price"], (int, float)):
                        try:
                            processed_item["price"] = float(processed_item["price"])
                        except (ValueError, TypeError):
                            processed_item["price"] = 0.0
                    processed_team_transfer_history.append(processed_item)
                elif isinstance(item, str):
                    processed_team_transfer_history.append({
                        "type": item,
                        "player_name": "N/A (Malformed Entry)",
                        "price": 0.0,
                        "success": False,
                        "day_of_window": None,
                        "message": "Original entry was a malformed string."
                    })
            
            team_detail = {
                "name": team_obj.name,
                "budget": team_obj.budget,
                "manager_name": team_obj.manager.name if team_obj.manager else "N/A",
                "manager_formation": team_obj.manager.formation if team_obj.manager else "N/A",
                "manager_experience": team_obj.manager.experience_level if team_obj.manager else 0,
                "squad_strength": team_obj.get_squad_strength(),
                "players": players_data,
                "team_season_stats": self.standings.get(team_obj.name, {}),
                "team_transfer_history": processed_team_transfer_history
            }
            all_teams_details.append(team_detail)

        # Transfer summary
        total_transfer_spending = {}
        total_transfer_activity = {}
        for tf_record in self.transfer_market.transfer_history:
            # Spending
            if tf_record['to_team'] not in total_transfer_spending:
                total_transfer_spending[tf_record['to_team']] = 0
            total_transfer_spending[tf_record['to_team']] += tf_record['amount']
            # Activity
            if tf_record['to_team'] not in total_transfer_activity:
                total_transfer_activity[tf_record['to_team']] = 0
            total_transfer_activity[tf_record['to_team']] += 1
            if tf_record['from_team'] not in total_transfer_activity:
                total_transfer_activity[tf_record['from_team']] = 0
            total_transfer_activity[tf_record['from_team']] += 1

        biggest_spenders_list = sorted(total_transfer_spending.items(), key=lambda item: item[1], reverse=True)[:5]
        most_active_list = sorted(total_transfer_activity.items(), key=lambda item: item[1], reverse=True)[:5]

        report = {
            "season": self.season_year,
            "champions": self.get_league_table()[0][0] if self.get_league_table() else "N/A",
            "champions_manager": self.get_best_manager(),
            "table": self.get_league_table(),
            "transfers": {
                "total_transfers": len(self.transfer_market.transfer_history),
                "biggest_spenders": biggest_spenders_list,
                "most_active": most_active_list,
                "all_completed_transfers": self.transfer_market.transfer_history
            },
            "best_players": self.get_best_players(),
            "season_stats": {
                "total_matches": len(self.schedule),
                "total_goals": sum(t_stats['gf'] for _, t_stats in self.standings.items()),
                "average_goals_per_match": (sum(t_stats['gf'] for _, t_stats in self.standings.items()) / len(self.schedule)) if self.schedule else 0,
                "best_attack": max(self.standings.items(), key=lambda x: x[1]['gf']) if self.standings else ("N/A", {"gf": 0}),
                "best_defense": min(self.standings.items(), key=lambda x: x[1]['ga']) if self.standings else ("N/A", {"ga": 0})
            },
            "all_teams_details": all_teams_details
        }
        return report

    def _init_season(self):
        """Initialize/reset season-specific data"""
        if self.standings:  # Only append if there are standings to save
            self.historical_standings.append((self.season_year, self.standings))
        self.standings = {}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Football League Simulation')
    parser.add_argument('--seasons', type=int, default=1, help='Number of seasons to simulate')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    # Helper function for debug output
    def debug_print(*msg, **kwargs):
        if args.debug:
            print(*msg, **kwargs)

    # Create league with smaller number of teams for testing
    league = League("Debug League", num_teams=6)
    debug_print(f"\nCreated league with {len(league.teams)} teams")

    # Enable debug mode for managers if --debug flag is set
    if args.debug:
        for team in league.teams:
            if team.manager:
                team.manager.set_debug(True)
                debug_print(f"Enabled debug mode for {team.manager.name} ({team.name})")

    debug_print(f"\nStarting {args.seasons} season simulation...")

    for season in range(args.seasons):
        debug_print(f"\n{'='*50}")
        debug_print(f"Season {season + 1}")
        debug_print(f"{'='*50}")
        
        league.generate_schedule()
        league.play_season()
        
        # Print season summary in debug mode
        if args.debug:
            standings = league.get_league_table()
            debug_print("\nFinal Standings:")
            debug_print(f"{'Team':<20} {'Pts':>3} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>3} {'GA':>3} {'GD':>3}")
            debug_print('-' * 55)
            for team_name, stats in standings:
                debug_print(f"{team_name:<20} {stats['points']:>3} {stats['played']:>3} "
                          f"{stats['won']:>3} {stats['drawn']:>3} {stats['lost']:>3} "
                          f"{stats['gf']:>3} {stats['ga']:>3} {stats['gd']:>3}")
            
            best_manager = league.get_best_manager()
            debug_print(f"\nBest Manager: {best_manager['name']}")
            debug_print(f"Formation: {best_manager['formation']}")
            debug_print(f"Transfer Success Rate: {best_manager['transfer_success_rate']*100:.1f}%")
        
        league.increment_season()
