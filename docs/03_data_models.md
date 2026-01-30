# 03. Data Models

This document outlines the data structures used in the project, covering both the SQLite database schema and the Python object classes.

## 1. Database Schema (`football_sim.db`)

The database is normalized to store long-term data for teams, players, and match history.

### Core Tables

#### `League`
*   `league_id` (PK): Unique ID.
*   `name`: League name (e.g., "Premier League").
*   `season_year`: Current season (e.g., 2024).

#### `Team`
*   `team_id` (PK): Unique ID.
*   `name`: Team name (Unique).
*   `budget`: Total funds available.
*   `transfer_budget`, `wage_budget`: Allocated portions of the budget.
*   `manager_id` (FK): Link to the `Manager` table.

#### `Player`
*   `player_id` (PK): Unique ID.
*   `name`: Player name.
*   `age`: Current age.
*   `position`: e.g., "ST", "GK", "CM".
*   `team_id` (FK): Current team.
*   `potential`: Max possible rating (0-100).
*   `wage`: Weekly salary.
*   `contract_length`: Years remaining.
*   `squad_role`: "STARTER", "BENCH", "RESERVE", or "YOUTH".

#### `Manager`
*   `manager_id` (PK): Unique ID.
*   `name`: Manager name.
*   `experience_level`: Affects training and transfer success.
*   `team_id` (FK): Current team.
*   `formation`: Preferred formation (e.g., "4-4-2").
*   `profile_id` (FK): Link to personality profile.

#### `Match`
*   `match_id` (PK): Unique ID.
*   `season_year`: Season the match belongs to.
*   `home_team_id` (FK), `away_team_id` (FK).
*   `home_goals`, `away_goals`.
*   `date`: Date played.

### Detail Tables

*   **`PlayerAttributes`**: Stores specific stats (pace, shooting, etc.) for each player. (One-to-Many with Player).
*   **`PlayerStats`**: Aggregates season stats (goals, assists, cards).
*   **`MatchEvent`**: Logs every significant event (goal, card, substitution) linked to a `match_id`.
*   **`TransferHistory`**: Logs completed transfers (player, from_team, to_team, amount, date).

## 2. Python Object Models

The Python classes mirror the database but include logic for the simulation.

### `League` (in `league.py`)
*   **Responsibilities**:
    *   Holds list of `Team` objects.
    *   Generates match schedule (`generate_schedule`).
    *   Runs the season loop (`play_season`).
    *   Maintains the `standings` table (Points, GD, etc.).

### `Team` (in `team.py`)
*   **Attributes**:
    *   `players`: List of `FootballPlayer` objects.
    *   `manager`: `Manager` object.
    *   `budget`: Float representing finances.
    *   `youth_academy`: List of young `FootballPlayer` objects not yet in the senior squad.
*   **Key Methods**:
    *   `process_weekly_finances()`: Updates budget based on wages and revenue.
    *   `calculate_matchday_revenue()`: Adds ticket sales after home games.
    *   `get_squad_strength()`: Returns average rating of active players.

### `FootballPlayer` (in `player.py`)
*   **Attributes**:
    *   `attributes`: Nested dict (e.g., `shooting: {finishing: 80, ...}`).
    *   `stats`: Season performance (goals, fitness, cards).
    *   `form`: List of recent match ratings.
*   **Key Methods**:
    *   `train_player()`: Improves attributes based on intensity.
    *   `apply_age_decline()`: Reduces attributes for older players.
    *   `get_overall_rating()`: Calculates a single 0-100 score from attributes.

### `Manager` (in `manager.py`)
*   **Attributes**:
    *   `brain`: Instance of `ManagerBrain` (Q-Learning).
    *   `tactics`: Dict of sliders (offensive, defensive, pressure).
*   **Key Methods**:
    *   `make_transfer_decision()`: Decides to buy/sell based on market state.
    *   `select_lineup()`: Picks best 11 based on fitness and rating.
    *   `learn_from_match()`: Updates Q-Table based on match outcome.

### `Match` (in `match.py`)
*   **Attributes**:
    *   `home_team`, `away_team`.
    *   `minute`: Current match time (0-90).
    *   `score`: [home, away].
    *   `events`: List of events.
*   **Key Methods**:
    *   `simulate_minute()`: Resolves one minute of gameplay.
    *   `play_match()`: Runs the full simulation and returns the result.
