from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table, Boolean, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Many-to-Many Association Tables
league_teams_association = Table(
    'LeagueTeams',
    Base.metadata,
    Column('league_id', Integer, ForeignKey('League.league_id'), primary_key=True),
    Column('team_id', Integer, ForeignKey('Team.team_id'), primary_key=True),
    Column('season_year', Integer, primary_key=True)
)

team_coaches_association = Table(
    'TeamCoaches',
    Base.metadata,
    Column('team_id', Integer, ForeignKey('Team.team_id'), primary_key=True),
    Column('coach_id', Integer, ForeignKey('Coach.coach_id'), primary_key=True)
)

class League(Base):
    __tablename__ = 'League'
    
    league_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    season_year = Column(Integer, nullable=False)
    
    teams = relationship("Team", secondary=league_teams_association, back_populates="leagues")

class Team(Base):
    __tablename__ = 'Team'
    
    team_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    budget = Column(Float, nullable=False)
    weekly_budget = Column(Float, nullable=False)
    transfer_budget = Column(Float, nullable=False)
    wage_budget = Column(Float, nullable=False)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'))

    manager = relationship("Manager", foreign_keys=[manager_id], uselist=False)
    leagues = relationship("League", secondary=league_teams_association, back_populates="teams")
    statistics = relationship("TeamStatistics", back_populates="team", uselist=False)
    coaches = relationship("Coach", secondary=team_coaches_association, back_populates="teams")
    players = relationship("Player", back_populates="team")

class TeamStatistics(Base):
    __tablename__ = 'TeamStatistics'
    
    team_id = Column(Integer, ForeignKey('Team.team_id'), primary_key=True)
    wins = Column(Integer, nullable=False, default=0)
    draws = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    goals_for = Column(Integer, nullable=False, default=0)
    goals_against = Column(Integer, nullable=False, default=0)
    
    team = relationship("Team", back_populates="statistics")

class Manager(Base):
    __tablename__ = 'Manager'
    
    manager_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    experience_level = Column(Integer, nullable=False)
    team_id = Column(Integer, ForeignKey('Team.team_id'))
    profile_id = Column(Integer, ForeignKey('ManagerProfile.profile_id'))
    transfers_made = Column(Integer, nullable=False, default=0)
    successful_transfers = Column(Integer, nullable=False, default=0)
    formation = Column(String, nullable=False)
    matches_played = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)
    draws = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    total_rewards = Column(Float, nullable=False, default=0.0)
    
    team = relationship("Team", foreign_keys=[team_id], overlaps="manager")
    tactics = relationship("ManagerTactics", back_populates="manager", uselist=False)
    profile = relationship("ManagerProfile")

class ManagerTactics(Base):
    __tablename__ = 'ManagerTactics'
    
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), primary_key=True)
    offensive = Column(Integer, nullable=False)
    defensive = Column(Integer, nullable=False)
    pressure = Column(Integer, nullable=False)
    
    manager = relationship("Manager", back_populates="tactics")

class ManagerProfile(Base):
    __tablename__ = 'ManagerProfile'
    
    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    risk_aversion = Column(Float, nullable=False)
    financial_preference = Column(Float, nullable=False)
    youth_preference = Column(Float, nullable=False)
    aggression = Column(Float, nullable=False)
    patience = Column(Float, nullable=False)

class Coach(Base):
    __tablename__ = 'Coach'
    
    coach_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    experience_level = Column(Integer, nullable=False)
    team_id = Column(Integer, ForeignKey('Team.team_id'))
    learning_rate = Column(Float, nullable=False)
    exploration_rate = Column(Float, nullable=False)
    
    teams = relationship("Team", secondary=team_coaches_association, back_populates="coaches")

class Player(Base):
    __tablename__ = 'Player'
    
    player_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    age = Column(Integer, nullable=False)
    position = Column(String, nullable=False)
    team_id = Column(Integer, ForeignKey('Team.team_id'))
    potential = Column(Integer, nullable=False)
    wage = Column(Float, nullable=False)
    contract_length = Column(Integer, nullable=False)
    squad_role = Column(String, nullable=False)
    
    team = relationship("Team", back_populates="players")
    attributes = relationship("PlayerAttribute", back_populates="player")
    stats = relationship("PlayerStat", back_populates="player", uselist=False)

class PlayerAttribute(Base):
    __tablename__ = 'PlayerAttributes'
    
    player_id = Column(Integer, ForeignKey('Player.player_id'), primary_key=True)
    attribute_type = Column(String, nullable=False, primary_key=True)
    sub_attribute = Column(String, nullable=False, primary_key=True)
    value = Column(Float, nullable=False)
    
    player = relationship("Player", back_populates="attributes")

class PlayerStat(Base):
    __tablename__ = 'PlayerStats'
    
    player_id = Column(Integer, ForeignKey('Player.player_id'), primary_key=True)
    goals = Column(Integer, nullable=False, default=0)
    assists = Column(Integer, nullable=False, default=0)
    appearances = Column(Integer, nullable=False, default=0)
    fitness = Column(Float, nullable=False, default=100.0)
    clean_sheets = Column(Integer, nullable=False, default=0)
    yellow_cards = Column(Integer, nullable=False, default=0)
    red_cards = Column(Integer, nullable=False, default=0)
    
    player = relationship("Player", back_populates="stats")

class Match(Base):
    __tablename__ = 'Match'
    __table_args__ = (Index('ix_match_season_year', 'season_year'),)
    
    match_id = Column(Integer, primary_key=True, autoincrement=True)
    match_number = Column(Integer, nullable=False)
    date = Column(String, nullable=False)
    season_year = Column(Integer, nullable=False)
    home_team_id = Column(Integer, nullable=False)
    away_team_id = Column(Integer, nullable=False)
    home_goals = Column(Integer, nullable=False, default=0)
    away_goals = Column(Integer, nullable=False, default=0)
    home_possession = Column(Float, nullable=False)
    away_possession = Column(Float, nullable=False)
    weather = Column(String, nullable=False)
    intensity = Column(String, nullable=False)
    home_passes_attempted = Column(Integer, nullable=False, default=0)
    away_passes_attempted = Column(Integer, nullable=False, default=0)
    home_passes_completed = Column(Integer, nullable=False, default=0)
    away_passes_completed = Column(Integer, nullable=False, default=0)
    home_fouls = Column(Integer, nullable=False, default=0)
    away_fouls = Column(Integer, nullable=False, default=0)
    home_corners = Column(Integer, nullable=False, default=0)
    away_corners = Column(Integer, nullable=False, default=0)
    home_offsides = Column(Integer, nullable=False, default=0)
    away_offsides = Column(Integer, nullable=False, default=0)
    home_yellow_cards = Column(Integer, nullable=False, default=0)
    away_yellow_cards = Column(Integer, nullable=False, default=0)
    home_red_cards = Column(Integer, nullable=False, default=0)
    away_red_cards = Column(Integer, nullable=False, default=0)
    home_injuries = Column(Integer, nullable=False, default=0)
    away_injuries = Column(Integer, nullable=False, default=0)

class SeasonReport(Base):
    __tablename__ = 'SeasonReport'
    
    report_id = Column(Integer, primary_key=True, autoincrement=True)
    season_year = Column(Integer, nullable=False, unique=True)
    champion_team = Column(String, nullable=False)
    report_data = Column(String, nullable=False) # JSON encoded data for easy historical querying
    created_at = Column(String, nullable=False)

class TransferReport(Base):
    __tablename__ = 'TransferReport'
    
    report_id = Column(Integer, primary_key=True, autoincrement=True)
    season_year = Column(Integer, nullable=False, unique=True)
    report_data = Column(String, nullable=False) # JSON encoded data
    created_at = Column(String, nullable=False)

class MatchShots(Base):
    __tablename__ = 'MatchShots'
    match_id = Column(Integer, ForeignKey('Match.match_id'), primary_key=True)
    team = Column(String, primary_key=True)  # 'home' or 'away'
    total = Column(Integer, nullable=False)
    on_target = Column(Integer, nullable=False)

class MatchEvent(Base):
    __tablename__ = 'MatchEvent'
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey('Match.match_id'), nullable=False)
    minute = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    player = Column(String)
    team = Column(String)
    details = Column(String)

class TransferListing(Base):
    __tablename__ = 'TransferListing'
    listing_id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('Player.player_id'), nullable=False)
    asking_price = Column(Float, nullable=False)
    selling_team_id = Column(Integer, ForeignKey('Team.team_id'), nullable=False)
    listed_date = Column(Integer, nullable=False)
    expires_in = Column(Integer, nullable=False)

class TransferHistory(Base):
    __tablename__ = 'TransferHistory'
    transfer_id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('Player.player_id'), nullable=False)
    from_team_id = Column(Integer, ForeignKey('Team.team_id'), nullable=False)
    to_team_id = Column(Integer, ForeignKey('Team.team_id'), nullable=False)
    amount = Column(Float, nullable=False)
    day = Column(Integer, nullable=False)
    season_year = Column(Integer, nullable=False)

class CoachTrainingEffectiveness(Base):
    __tablename__ = 'CoachTrainingEffectiveness'
    coach_id = Column(Integer, ForeignKey('Coach.coach_id'), primary_key=True)
    method = Column(String, primary_key=True)
    effectiveness = Column(Float, nullable=False)

class CoachSessionResults(Base):
    __tablename__ = 'CoachSessionResults'
    id = Column('rowid', Integer, primary_key=True)
    coach_id = Column(Integer, ForeignKey('Coach.coach_id'), nullable=False)
    method = Column(String, nullable=False)
    average_improvement = Column(Float, nullable=False)
    players_improved = Column(Integer, nullable=False)

class CoachPlayerProgress(Base):
    __tablename__ = 'CoachPlayerProgress'
    id = Column('rowid', Integer, primary_key=True)
    coach_id = Column(Integer, ForeignKey('Coach.coach_id'), nullable=False)
    player_name = Column(String, nullable=False)
    focus_attribute = Column(String, nullable=False)
    improvement = Column(String, nullable=False)

class ManagerTransferAttempts(Base):
    __tablename__ = 'ManagerTransferAttempts'
    id = Column('rowid', Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    attempt_successful = Column(Boolean, nullable=False)

class ManagerTransferValueEstimates(Base):
    __tablename__ = 'ManagerTransferValueEstimates'
    id = Column('rowid', Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    player_name = Column(String, nullable=False)
    estimated_value = Column(Float, nullable=False)

class ManagerMarketMemoryPriceHistory(Base):
    __tablename__ = 'ManagerMarketMemoryPriceHistory'
    id = Column('rowid', Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    position = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(String, nullable=False)

class ManagerMarketMemoryPositionDemand(Base):
    __tablename__ = 'ManagerMarketMemoryPositionDemand'
    id = Column('rowid', Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    position = Column(String, nullable=False)
    demand_value = Column(Float, nullable=False)
    timestamp = Column(String, nullable=False)

class ManagerMarketMemorySeasonalFactors(Base):
    __tablename__ = 'ManagerMarketMemorySeasonalFactors'
    id = Column('rowid', Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    month = Column(Integer, nullable=False)
    factor = Column(Float, nullable=False)

class ManagerMarketMemorySuccessPatterns(Base):
    __tablename__ = 'ManagerMarketMemorySuccessPatterns'
    id = Column('rowid', Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    pattern_data = Column(String, nullable=False)
    date = Column(String, nullable=False)

class ManagerTransferHistory(Base):
    __tablename__ = 'ManagerTransferHistory'
    transfer_id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('Player.player_id'), nullable=False)
    from_team_id = Column(Integer, ForeignKey('Team.team_id'), nullable=False)
    to_team_id = Column(Integer, ForeignKey('Team.team_id'), nullable=False)
    amount = Column(Float, nullable=False)
    day = Column(Integer, nullable=False)
    season_year = Column(Integer, nullable=False)

class ManagerMatchHistory(Base):
    __tablename__ = 'ManagerMatchHistory'
    id = Column('rowid', Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    match_data = Column(String, nullable=False)
    date = Column(String, nullable=False)

class ManagerLineupHistory(Base):
    __tablename__ = 'ManagerLineupHistory'
    lineup_id = Column(Integer, primary_key=True, autoincrement=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    match_id = Column(Integer, ForeignKey('Match.match_id'), nullable=False)
    date = Column(String, nullable=False)

manager_lineup_players_association = Table(
    'ManagerLineupPlayers',
    Base.metadata,
    Column('lineup_id', Integer, ForeignKey('ManagerLineupHistory.lineup_id'), primary_key=True),
    Column('player_id', Integer, ForeignKey('Player.player_id'), primary_key=True)
)

class ManagerPerformanceHistory(Base):
    __tablename__ = 'ManagerPerformanceHistory'
    performance_id = Column(Integer, primary_key=True, autoincrement=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    total_rewards = Column(Float, nullable=False)
    win_rate = Column(Float, nullable=False)
    draw_rate = Column(Float, nullable=False)
    exploration_rate = Column(Float, nullable=False)
    learning_rate = Column(Float, nullable=False)
    matches_played = Column(Integer, nullable=False)
    wins = Column(Integer, nullable=False)
    draws = Column(Integer, nullable=False)
    losses = Column(Integer, nullable=False)
    average_reward = Column(Float, nullable=False)
    transfer_success_rate = Column(Float, nullable=False)
    current_exploration_rate = Column(Float, nullable=False)
    date = Column(String, nullable=False)

class ManagerMarketLearning(Base):
    __tablename__ = 'ManagerMarketLearning'
    market_learning_id = Column(Integer, primary_key=True, autoincrement=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    price_trends = Column(String, nullable=False)
    position_demand = Column(String, nullable=False)
    seasonal_patterns = Column(String, nullable=False)
    date = Column(String, nullable=False)

class ManagerFormationPreferences(Base):
    __tablename__ = 'ManagerFormationPreferences'
    formation_preference_id = Column(Integer, primary_key=True, autoincrement=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    formation = Column(String, nullable=False)
    preference_weight = Column(Float, nullable=False)
    date = Column(String, nullable=False)

class ManagerMemoryUsage(Base):
    __tablename__ = 'ManagerMemoryUsage'
    memory_usage_id = Column(Integer, primary_key=True, autoincrement=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    transfer_history_size = Column(Integer, nullable=False)
    market_memory_size = Column(String, nullable=False)
    value_estimates_size = Column(Integer, nullable=False)
    date = Column(String, nullable=False)

class ManagerMarketStateHistory(Base):
    __tablename__ = 'ManagerMarketStateHistory'
    market_state_id = Column(Integer, primary_key=True, autoincrement=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    market_trend = Column(String, nullable=False)
    position_demand = Column(String, nullable=False)
    seasonal_factor = Column(String, nullable=False)
    date = Column(String, nullable=False)

class ManagerEpisodeRewards(Base):
    __tablename__ = 'ManagerEpisodeRewards'
    id = Column('rowid', Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    reward = Column(Float, nullable=False)

class ManagerMatchRewards(Base):
    __tablename__ = 'ManagerMatchRewards'
    id = Column('rowid', Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    reward = Column(Float, nullable=False)

class ManagerQTable(Base):
    __tablename__ = 'ManagerQTable'
    id = Column('rowid', Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('Manager.manager_id'), nullable=False)
    qtable_type = Column(String, nullable=False)
    qtable_data = Column(String, nullable=False)

class PlayerForm(Base):
    __tablename__ = 'PlayerForm'
    player_id = Column(Integer, ForeignKey('Player.player_id'), primary_key=True)
    form = Column(String, nullable=False)

class PlayerInjuryHistory(Base):
    __tablename__ = 'PlayerInjuryHistory'
    injury_id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('Player.player_id'), nullable=False)
    injury_type = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    date = Column(String, nullable=False)

class LeagueHistoricalStandings(Base):
    __tablename__ = 'LeagueHistoricalStandings'
    historical_standing_id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, ForeignKey('League.league_id'), nullable=False)
    season_year = Column(Integer, nullable=False)
    standings = Column(String, nullable=False)
