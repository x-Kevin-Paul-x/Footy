# 02. Backend Logic

This document details the core logic of the Python backend, including the simulation loop, AI decision-making, match engine, and transfer market.

## 1. Simulation Loop (`main.py`)

The simulation is driven by the `main.py` script (or via API triggers). The core function is `simulate_season_with_transfers`, which orchestrates the flow of time.

### Season Structure
A season runs through a specific calendar of days:
1.  **Summer Transfer Window (Days 1-61)**:
    *   The market is open.
    *   AI Managers actively scout, list, and buy players every few days.
    *   No matches are played during this phase.
2.  **First Half of Season**:
    *   Matches are scheduled and played.
    *   Weekly finances are processed (matchday revenue, wages).
    *   Players age and recover from injuries.
3.  **January Transfer Window (Days 183-214)**:
    *   Market re-opens for mid-season adjustments.
4.  **Second Half of Season**:
    *   Remaining matches are played.
    *   Champion is crowned.
5.  **End of Season**:
    *   Contract expiries are processed.
    *   Awards (Player of the Season) are calculated.
    *   Reports are generated and saved to JSON.

## 2. Manager AI (`manager.py` & `manager_brain.py`)

The AI uses **Reinforcement Learning (Q-Learning)** to make decisions. Each team has a `Manager` instance with a `ManagerBrain`.

### State Encoding
The raw game state is complex, so `StateEncoder` discretizes it into a tuple for the Q-table:
*   **Squad State**: Squad size (normalized), average age, role gaps, position balance.
*   **Financial State**: Budget utilization, wage bill status.
*   **Performance**: Form, goals scored/conceded.
*   **Market**: Market trends, season progress.

### Decision Making
The Manager makes three key types of decisions:
1.  **Transfers**:
    *   Scouts players based on team needs (weak positions).
    *   Uses Q-Learning to decide whether to `buy`, `sell`, or `wait` given the current market and squad state.
    *   Evaluates free agents if the squad is thin.
2.  **Lineups**:
    *   Selects a formation (e.g., 4-4-2, 4-3-3).
    *   Picks the best available players for that formation.
    *   Uses Q-Learning to optimize lineup selection over time.
3.  **Tactics**:
    *   Sets `offensive`, `defensive`, and `pressure` sliders (0-100).
    *   Adjusts tactics based on match results.

### Learning
After every action (Match or Transfer), the Manager receives a **Reward**:
*   **Match Reward**: Based on result (Win/Draw/Loss), goals, possession, and youth development.
*   **Transfer Reward**: Based on value-for-money, squad balance improvement, and financial health.
The `ManagerBrain` updates its Q-table using the standard Q-learning update rule to improve future decisions.

## 3. Match Engine (`match.py`)

Matches are simulated minute-by-minute in the `Match` class.

### Minute Loop
For every minute (0-90+):
1.  **Action Selection**: The engine determines the phase of play based on possession (Attack, Midfield, Defense).
2.  **Resolution**:
    *   **Pass**: Calculates success based on passer's vision vs. defender's marking + weather effects.
    *   **Tackle**: Calculates success based on tackling vs. dribbling. Failed tackles can lead to **Cards** (Yellow/Red).
    *   **Shot**: Calculates success based on shooting vs. goalkeeping. Successful shots result in **Goals**.
3.  **Events**: Goals, cards, injuries, and substitutions are logged as `MatchEvent` objects.
4.  **Fatigue & Injury**: Players lose stamina every minute. Low stamina increases injury risk.

### Key Features
*   **Home Advantage**: Home teams get a slight rating boost.
*   **Weather**: Rain, Snow, and Wind affect passing and shooting accuracy.
*   **Form**: Players in good form perform better.
*   **Position Penalty**: Players playing out of position suffer a performance penalty (e.g., a Striker playing as CB).

## 4. Transfer Market (`transfer.py`)

The `TransferMarket` class manages the economy of players.

### Valuation Logic
A player's market value is calculated based on:
*   **Overall Rating**: Base value.
*   **Age**: Peak age (25-28) carries a premium; older players are discounted.
*   **Potential**: Young players with high potential are valued higher.
*   **Contract**: Long contracts increase value; expiring contracts decrease it.
*   **Form**: Recent performance acts as a multiplier.

### Transfer Flow
1.  **Listing**: A team lists a player for sale (`TransferListing`).
2.  **Bidding**: AI Managers (or the user, potentially) make offers.
3.  **Negotiation**:
    *   Checks if the buying team has the budget.
    *   Checks if the offer meets the asking price (within a tolerance).
    *   **Wage Negotiation**: The player demands a wage based on the new club's prestige and budget.
4.  **Completion**:
    *   Funds are transferred.
    *   Player switches teams.
    *   Transaction is logged in `TransferHistory`.

### Free Agency
Players with expired contracts become **Free Agents**. Teams with small squads (under 16 players) can sign free agents outside of transfer windows to fill gaps.

## 5. Player Development (`player.py`)

*   **Training**: Players improve attributes based on training intensity and facilities.
*   **Age Decline**: Older players (30+) have a chance to lose attribute points periodically.
*   **Growth**: Young players improve faster, especially if they get match minutes.
