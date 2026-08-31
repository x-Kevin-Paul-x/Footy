---
name: match-engine-balancer
description: >-
  Procedure for calibrating, balancing, and benchmarking football simulation mechanics
  (xG calculation, goal frequencies, cards, injuries, fatigue, and tactical multipliers)
  against real-world Opta / Premier League standards. Triggers when modifying match engine parameters.
---

# Football Simulation Match Engine Balancer

This skill defines the statistical benchmarks and Monte Carlo validation protocols used to calibrate the match simulation engine in `Footy`.

---

## 1. Premier League & Opta Target Benchmarks

When calibrating `backend/src/models/match.py` or `match_engine_grf.py`, the outputs over a 100-match sample must stay within these realistic ranges:

| Metric | Realistic Target (per match) | Acceptable Tolerance Range |
| :--- | :--- | :--- |
| **Total Goals** | 2.80 | $2.60 - 3.10$ |
| **Home Win %** | $45.5\%$ | $42.0\% - 48.0\%$ |
| **Draw %** | $24.0\%$ | $21.0\% - 27.0\%$ |
| **Away Win %** | $30.5\%$ | $27.0\% - 33.0\%$ |
| **Total Shots** | 25.0 (13 home / 12 away) | $22.0 - 28.0$ |
| **Total xG** | 2.75 | $2.50 - 3.00$ |
| **Yellow Cards** | 3.80 | $3.20 - 4.40$ |
| **Red Cards** | 0.12 (1 per $\sim8$ matches) | $0.08 - 0.18$ |
| **In-Game Injuries** | 0.35 (1 per $\sim3$ matches) | $0.25 - 0.45$ |

---

## 2. Automated Monte Carlo Validation Protocol

Run an automated 100-match Monte Carlo calibration test using the following validation script:

```python
import numpy as np
from src.models.match import simulate_match  # or engine runner

def run_calibration_suite(n_matches=100):
    goals = []
    home_wins, draws, away_wins = 0, 0, 0
    cards = []
    
    for _ in range(n_matches):
        result = simulate_match("Arsenal", "Chelsea", "4-3-3", "4-2-3-1")
        h_score = result["home_score"]
        a_score = result["away_score"]
        goals.append(h_score + a_score)
        
        if h_score > a_score: home_wins += 1
        elif h_score == a_score: draws += 1
        else: away_wins += 1
        cards.append(len([e for e in result.get("timeline", []) if e.get("type") in ["yellow_card", "red_card"]]))
        
    avg_goals = np.mean(goals)
    print(f"Sample Size: {n_matches}")
    print(f"Avg Goals: {avg_goals:.2f} (Target: 2.7-3.0)")
    print(f"Home Win Rate: {(home_wins/n_matches)*100:.1f}% (Target: ~45%)")
    print(f"Draw Rate: {(draws/n_matches)*100:.1f}% (Target: ~24%)")
    print(f"Away Win Rate: {(away_wins/n_matches)*100:.1f}% (Target: ~31%)")
    print(f"Avg Cards: {np.mean(cards):.2f} (Target: ~3.8)")
    
    assert 2.4 <= avg_goals <= 3.4, "Goal scoring distribution is out of balance!"
```

---

## 3. Balancing Mechanics Quick Reference

* **If too many goals**: Reduce base shot conversion probability factor or increase goalkeeper save multiplier.
* **If home advantage is too high ($>55\%$)**: Lower home stadium pitch familiarity modifier from e.g. $+0.12$ down to $+0.05$.
* **If cards are too frequent**: Increase foul threshold check before card check.
* **Fatigue decay**: Linear fatigue decay should result in an average of $78-85\%$ stamina by the 70th minute to encourage tactical substitutions.
