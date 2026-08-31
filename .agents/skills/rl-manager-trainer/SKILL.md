---
name: rl-manager-trainer
description: >-
  Playbook for training, evaluating, and benchmarking Deep Reinforcement Learning (DQN)
  manager brains in PyTorch. Triggers when modifying manager ML models, reward functions,
  state encoders, or running benchmark evaluations.
---

# PyTorch Deep Reinforcement Learning (DQN) Manager Trainer

This skill guides the design, training, and benchmarking of AI Manager Brains (`backend/src/ml/`).

---

## 1. Manager State & Action Space Architecture

### State Representation (Vectorized 12-dim Float)
1. **League Position / Percentile** ($0.0 - 1.0$)
2. **Recent 5-Match Form** (Points per game normalized: $[0, 3] \rightarrow [0, 1]$)
3. **Average Squad Overall Rating (OVR)** ($[50, 95] \rightarrow [0, 1]$)
4. **Squad Depth Score** (Ratio of healthy outfield players to starting XI)
5. **Wage-to-Turnover Ratio** (Financial health: healthy $< 0.65$, critical $> 0.90$)
6. **Transfer Budget Availability** (Normalized against league median)
7. **Opponent Relative Strength** ($\Delta \text{OVR} \in [-1.0, 1.0]$)
8. **Board Confidence Rating** ($0.0 - 1.0$)

### Discrete Action Space (Formations & Tactics)
* Actions correspond to tactical manager decisions:
  - `0`: 4-3-3 Balanced
  - `1`: 4-3-3 High Press (Gegenpress)
  - `2`: 4-2-3-1 Possession (Tiki-Taka)
  - `3`: 3-5-2 Direct Counter-Attack
  - `4`: 5-3-2 Defensive (Park the Bus)
  - `5`: Youth Rotation (Prioritize U21 players)

---

## 2. Reward Function Design

Rewards are calculated at the end of each fixture and season:

$$\text{Reward} = R_{\text{match}} + R_{\text{form}} + R_{\text{financial}} + R_{\text{youth}}$$

* **Match Outcome ($R_{\text{match}}$)**:
  - Win: $+3.0$
  - Draw against stronger opponent: $+1.5$
  - Draw against weaker opponent: $+0.5$
  - Loss: $-1.5$
* **Financial Prudence ($R_{\text{financial}}$)**:
  - Penalty for exceeding wage budget: $-2.0 \times (\text{WageRatio} - 0.70)$
* **Youth Development ($R_{\text{youth}}$)**:
  - Bonus for starting academy graduates: $+0.4$ per youth start.

---

## 3. Training & Benchmarking Runbook

### Running Training
```powershell
python backend/src/ml/train_rl.py --episodes 500 --batch-size 64 --gamma 0.99 --lr 0.0005
```

### Benchmarking Protocol
Compare the trained DQN policy against three baseline heuristics over 3 full seasons:
1. **Random Action Policy**: Random valid tactical selection.
2. **Static Heuristic**: Always play preferred formation (e.g. 4-3-3).
3. **Rule-Based Tactician**: Selects defensive against top 4 teams, attacking against bottom 4 teams.

Target: Trained DQN policy should achieve at least a **$+18\%$ higher win rate** and **better average league finish** than static heuristics.
