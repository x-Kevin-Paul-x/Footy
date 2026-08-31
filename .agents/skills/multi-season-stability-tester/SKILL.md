---
name: multi-season-stability-tester
description: >-
  Procedure for running multi-season stress tests (5-10 seasons) to detect simulation crashes,
  economic inflation/bankruptcy bugs, squad depletion glitches, aging curve degradation,
  and memory leaks. Triggers when making major gameplay or calendar changes.
---

# Multi-Season Stability & Economy Stress Tester

This skill provides testing protocols for long-term simulation health across 5 to 10 continuous seasons in `Footy`.

---

## 1. Key Invariants to Verify Across 5+ Seasons

1. **Squad Size & Positional Balance**:
   - Every club must maintain at least 2 Goalkeepers, 6 Defenders, 6 Midfielders, and 4 Forwards.
   - Thin squads must trigger emergency free agency signings during transfer windows.
2. **Economic Health**:
   - Total league money supply must not undergo runaway hyperinflation ($>15\%$ per season) or collapse into universal debt.
   - Player valuations must remain calibrated ($£1\text{M} - £150\text{M}$).
3. **Player Aging & Retirement**:
   - Players peak between ages 26–29.
   - Attributes decline moderately after age 30, accelerating after age 33.
   - Retirements between ages 34–38 with automatic replenishment via Youth Academy generation.
4. **Memory & Performance**:
   - Memory usage (RAM) must remain flat across consecutive season runs.
   - Unneeded intermediate frame tensors and temporary logs must be cleaned up after each matchday.

---

## 2. Multi-Season Test Execution Runbook

Run the 3-season or 10-season simulation harness:

```powershell
# Run from backend root
python backend/run_3_seasons.py
```

### Verification Checklist Post-Run:
* [ ] All 38 matchdays simulated for each season with 0 unhandled exceptions.
* [ ] Standings table properly reset at the start of each new season (points back to 0, goal difference to 0).
* [ ] Relegation / European qualification flags correctly updated.
* [ ] Database contains valid historical snapshots in SQLite (`football_sim.db`).
* [ ] JSON reports in `backend/reports/` are valid and parseable by the React frontend.
