# Footy: A Football League Simulation in Python

## Project Description

Footy is a Python-based simulation of a football (soccer) league. It models various aspects of football management, including team management, player development, match simulation, and a transfer market. The simulation incorporates elements of reinforcement learning for manager decision-making and player training.

## Files Description

- **coach.py**: Defines the `Coach` class, which represents football coaches with specializations and learning capabilities. Coaches can conduct training sessions to improve players' attributes and adapt their training approaches based on player progress.

- **league.py**: Defines the `League` class, which manages a football league. It handles team creation, match scheduling (double round-robin), season simulation, league standings, and transfer windows. It also generates season reports and identifies the best-performing manager and players.

- **main.py**: Contains the main execution script to create and simulate a Premier League season. It sets up teams with realistic budgets, creates player squads, simulates the season, prints league standings, and generates a season report in JSON format.

- **manager.py**: Defines the `Manager` class, representing football team managers. Managers in this simulation employ reinforcement learning to make decisions such as team formation, tactical adjustments during matches, player lineups, and transfer strategies.

- **match.py**: Defines the `Match` class, which simulates a single football match between two teams. It calculates match events, scores, possession, and player fatigue based on team and player attributes, tactics, and random factors like weather and match intensity.

- **player.py**: Defines the `FootballPlayer` class, representing football players with various attributes (pace, shooting, passing, dribbling, defending, physical, goalkeeping), potential, and statistics. Players can be created with randomized attributes and trained to improve their skills.

- **team.py**: Defines the `Team` class, representing a football team. It manages team budgets, players, managers, coaches, and team statistics. Teams can handle player transfers, calculate squad strength, and analyze squad needs.

- **transfer.py**: Defines classes related to the transfer market: `TransferListing` and `TransferMarket`. The `TransferMarket` class manages player listings, calculates player values, and simulates transfer offers and completions, including AI-driven transfers by simulated teams.

## How to Run the Simulation

1. **Prerequisites:**
   - Python 3.x
   - Libraries: `names`, `numpy`

   You can install the required libraries using pip:
   ```bash
   pip install names numpy
   ```

2. **Run the main script:**
   Navigate to the project directory in your terminal and execute:
   ```bash
   python main.py
   ```

   This script will:
   - Create a simulated Premier League with 20 teams.
   - Generate a season schedule.
   - Simulate the entire season, match by match.
   - Print the final league standings.
   - Print the team of the season (best XI players).
   - Save a detailed season report to `season_report.json`.
   - Match reports for each match are saved in the `match_reports/` directory.

## Potential Improvements and Future Features

- **Enhanced Player Development:** Implement more detailed player progression based on age, training regimes, and performance.
- **Tactical Depth:** Expand tactical options and their impact on match outcomes.
- **Financial Simulation:** Develop a more complex financial model including sponsorships, merchandise, and stadium management.
- **User Interface:** Create a user interface (text-based or GUI) to interact with the simulation, manage teams, and view match results in real-time.
- **More Detailed Match Events:** Add more types of match events like yellow/red cards, injuries, substitutions, and detailed commentary.
- **Advanced AI Opponents:** Improve the AI for team managers to make more strategic decisions in transfers, tactics, and player management.
- **Data Visualization:** Include data visualization for season reports, player stats, and league performance over time.
- **Customizable Leagues:** Allow users to create custom leagues with different configurations, numbers of teams, and rules.

This project provides a foundation for a comprehensive football league simulation and can be expanded in many directions to add more realism and features.
