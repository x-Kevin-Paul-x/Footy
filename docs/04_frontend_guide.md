# 04. Frontend Guide

Last verified: **6 September 2026**

## Stack

- React 19.1 and React DOM 19.1
- TypeScript 5.8 and Vite 6.3
- Material UI 5, Tailwind CSS 4, Emotion
- React Query 5 for server data
- Zustand 5 for simulation/season state
- Axios, Recharts, React Router 7

## Structure

| Path | Responsibility |
| --- | --- |
| `src/App.tsx` | Layout, lazy routes, global toast/error boundary. |
| `src/pages/Dashboard.tsx` | Season overview, matches, engine/settings, simulation trigger/progress. |
| `src/pages/MatchDetail.tsx` | Match statistics, events, lineups, replay generation. |
| `src/components/MatchVideoReplay.tsx` | Video playback, render polling, timeline-aware seek helpers. |
| `src/components/FormationViewer.tsx` | Responsive percentage-based pitch formation. |
| `src/components/HeaderSettingsModal.tsx` | Local API/toast settings and backend simulation settings. |
| `src/services/api.ts` | Axios contracts and endpoint functions. |
| `src/hooks/useSimulationSocket.ts` | WebSocket lifecycle and reconnect backoff. |
| `src/store/simulationStore.ts` | Zustand season/report/simulation actions. |

## Data flow

React Query loads most dashboard and detail resources. Zustand also loads seasons/reports and implements a separate simulation flow. The WebSocket hook receives `{event, message, data}` frames and can invalidate/refetch UI state. Replay rendering is polled using completion-scheduled `setTimeout`, avoiding overlapping requests.

The formation component positions players using percentages plus `translate(-50%, -50%)`, which prevents fixed-width pitch clipping.

## API configuration

Development currently defaults to `http://localhost:5001`. The Axios client reads `process.env.VITE_API_BASE_URL` when `services/api.ts` loads; Vite supplies a compatibility define. The WebSocket hook also checks `localStorage.footy_api_url` and `import.meta.env`.

The settings modal writes `footy_api_url`, but Axios does not read that local value. Until the client is centralized, changing the API URL does not update REST requests.

`getSeasonReportData()` currently converts every request failure into `null`. This makes an unavailable backend or HTTP 500 look like a season with no report and prevents several page-level error states from appearing. It should return `null` only for the defined not-found case and propagate other failures.

## Known integration defects

1. The backend season trigger returns success without `run_id`; Dashboard and Zustand expect it for polling.
2. `runMlEvaluation()` expects `{status, report}`, while the backend returns HTTP 202 with only `{status, message}` and offers no job-status endpoint. The ML work also executes synchronous episode loops inside the API event loop.
3. Timeline-aware seeking is approximate for 3D paths whose frame inserts differ from the shared timeline defaults.
4. React Query and Zustand duplicate server-owned season/simulation state.
5. Existing frontend tests cover two components and do not cover the above workflows, replay controls, responsive breakpoints, or accessibility.

## Main API resources used

| Resource | Purpose |
| --- | --- |
| `GET /api/v1/seasons` and `/season-report/{year}` | Season selection and report data. |
| `GET /api/v1/seasons/{season_year}/matches` and `/api/v1/match/{id}` | Match lists and detail. The season path is deliberately distinct from the single-match resource. |
| `POST /api/v1/run-simulation` | Start season simulation. Contract currently lacks returned run ID. |
| `GET /api/v1/simulation/current-run` | Most recent run metadata. |
| `POST /api/v1/match/simulate-grf` | On-demand GRF match. |
| `POST /api/v1/match/{id}/render` | On-demand replay render. |
| `GET /api/v1/match/{id}/render-status` | Render progress. |
| `GET /api/v1/match/{id}/timeline` | Presentation time mapping. |
| `GET/POST /api/v1/settings/simulation` | Render mode/model settings. |
| `GET /api/v1/ml-reports`, `POST /api/v1/run-ml-eval` | ML reports and evaluation trigger. |

## Validation

Verified locally:

```text
TypeScript no-emit: passed
Vite production build: passed; 2,225 modules transformed
Jest: 2 suites, 6 tests passed
```

The production build warns that Browserslist data is seven months old. Updating that data is maintenance, not a correctness blocker.
