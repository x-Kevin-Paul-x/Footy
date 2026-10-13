# Verification — 13 October 2026

This report records the project-roadmap branch checks. Raw policy, calibration, training and performance evidence is in [evidence/](evidence/). Counts describe the checks actually run, not a guarantee about every supported environment.

## Checks

| Check | Evidence |
| --- | --- |
| Full Windows backend suite with coverage | Final combined backend/commentary pass: 177 passed, 11 skipped in 312.40 seconds. Coverage XML generated; the additional V1/V3/archive-loader suite passed 41 tests with one environment skip. |
| Commentary work already present in the workspace | 21 passed in 1.98 seconds. |
| Focused migration/job/API/economy checks | 43 passed; an additional real evaluation API/process run passed its five-test suite. |
| Frontend | 13 tests passed across six suites, including job polling, refresh recovery, shared API/WS configuration and saved-campaign cash history. |
| Backend lint / scoped typing | Ruff runtime/syntax gate passed; mypy passed for the configured path/timeline modules. |
| Frontend production build | Passed. Existing bundle-size and stale Browserslist notices remain informational. |
| Clean GitHub verification | [Run 38470099412](https://github.com/x-Kevin-Paul-x/Footy/actions/runs/38470099412) passed: 168 backend/commentary tests, 22 explicit environment/legacy skips, 44% portable source coverage; 13 frontend tests plus lint, typing and production build. |
| Final portability and error checks | 51 affected checks passed locally, including native match API calls; the final report-error suite passed 14 tests. Native runtime unavailability returns 503, and missing reports retain 404. |
| Public demo | [Live static demo](https://x-kevin-paul-x.github.io/Footy/) deployed after CI. Results/calibration loaded in the browser; video played with 310.7-second duration and no media error. |
| Root dependency audit | Compatible lodash/shell-quote updates applied; zero reported vulnerabilities in the root launcher and frontend dependency trees after compatible fixes and a clean frontend installation. |
| Real native benchmark | One and two workers observed, repeated canonical outcomes and topology comparison passed. [Raw report](evidence/native_benchmark.json). |
| Training and policy comparison | Three 100-episode training runs, seeds 42–44; 30 held-out seeds per policy. [Raw results](evidence/manager_evaluation.json). |
| Five-season domain/economy soak | Cashflow reconciliation, no insolvency, retirement/positional replenishment, bounded academies and 15% annual cash retention checked. [Report](evidence/multi_season_stress.json). |
| Calibration | Read-only audit of the retained 380-fixture native season against the 2023/24 reference, with dataset checksum and source attribution. [Report](evidence/calibration.json). |

## Native determinism

The first direct Linux topology check exposed different archive hashes even though scores matched. The pooled executor recorded policy provenance while the direct executor did not. Policy actions now carry stable provenance into every executor entry point; filesystem checkpoint paths are not used as canonical policy identity.

The rerun checks six seeds at one, eight, twelve and sixteen workers, with sixteen simultaneous fixtures in each populated pool. Raw trajectory archives must match the corresponding single-worker baseline. Separate tests check worker IDs 0/3/7/11 and controlled crashes at steps 300, 600 and 900. All three direct Linux checks passed in 854.68 seconds. The native XML result is summarized in [verification summary](evidence/verification_summary.json).

The one/two-worker performance diagnostic uses 200-step partial matches; the topology/worker tests use 1,200-step traces. These prove their stated execution invariants, not full-season outcome realism or GPU-policy equivalence.

## Scope and limitations

- Windows skips tests importing native `gfootball` directly; those require the Linux runtime. Windows/WSL adapter tests and direct-Linux tests are different suites.
- The management evaluation environment is synthetic. It does not validate the physical match engine, and the new DQN runs did not beat random actions in this sample.
- Native substitutions remain unsupported. `FOOTY_DYNAMIC_TACTICS=1` is an experimental policy-modulation profile; the default official TiKick profile is preserved.
- The retained season still scores more frequently than the real reference. Calibration evidence is published without changing authoritative scores to meet a target.
- Database snapshots retain committed history and pinned artifacts; live in-memory campaign continuation is not implemented.
- The read-only demo is deployed through GitHub Pages. The v0.1.0 release is an unpublished draft with generated manager checkpoints, provenance and checksums; it is available to the repository owner for review.

Coverage and native test limitations are explicit so that a skipped or synthetic check cannot be mistaken for production verification.
