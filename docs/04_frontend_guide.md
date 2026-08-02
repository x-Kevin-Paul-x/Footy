# 04. Frontend Guide

This document explains the structure and functionality of the React Frontend located in the `frontend/` directory.

## Tech Stack
*   **Framework**: React 19 (via Vite)
*   **Language**: TypeScript
*   **Styling**: Tailwind CSS
*   **HTTP Client**: Axios
*   **Charts**: Chart.js (via react-chartjs-2)
*   **State Management**: Zustand (implied) + React Hooks

## Directory Structure

```
frontend/src/
├── components/         # UI Components (Views & Widgets)
├── services/           # API integration
├── store/              # State management (Zustand)
├── App.tsx             # Main routing and layout
└── main.tsx            # Entry point
```

## API Integration (`services/api.ts`)

The frontend communicates with the FastAPI backend via `http://localhost:5001`.

### Key Functions
*   `runSimulation()`: Triggers the backend simulation (POST `/run-simulation`).
*   `getAvailableSeasons()`: Fetches list of years with available data.
*   `getSeasonReportData(year)`: Loads the full JSON report for a specific season.
*   `getMatchesBySeason(year)`: Fetches match schedule/results.

### Data Interfaces
TypeScript interfaces define the shape of the data:
*   `SeasonReport`: The massive object containing the entire season's output (Table, Top Players, Transfers, Team Details).
*   `TeamDetail`: Detailed stats for a specific team, including roster and finances.
*   `Player`: Attributes, stats, and contract info.

## Key Components

### 1. Dashboard (`Dashboard.tsx`)
The landing page. likely displays the most recent league table and key metrics.

### 2. Season Reports (`SeasonReports.tsx`)
The core view for analyzing simulation results. It likely includes:
*   **League Table**: Uses `StandingsTable.tsx`.
*   **Champions Info**: Displays the winner and manager of the season.
*   **Stats**: Top scorers, assists, etc.

### 3. Team Details (`TeamDetails.tsx`)
A deep dive into a specific team.
*   **Roster**: List of players with ratings and positions (`PlayerProfiles.tsx`?).
*   **Finances**: Charts showing revenue/expenses (`FinancialChart.tsx`).
*   **Manager**: Info on the current manager and tactics (`ManagerDetail.tsx`).

### 4. Player Details (`PlayerDetail.tsx`)
Individual player profile showing:
*   **Attributes**: Radar chart or list of skills (Pace, Shooting, etc.).
*   **History**: Stats (goals, apps) and injury history.
*   **Contract**: Wage and value.

### 5. Transfer Market (`TransferMarket.tsx`)
Visualizes the transfer activity:
*   Biggest spenders.
*   Recent transfers list.

## Development Workflow

1.  **Start Backend**: `python api_fastapi.py` (Port 5001).
2.  **Start Frontend**: `npm run dev` (Port 5173).
3.  **Simulate**: Click "Run Simulation" in the UI to generate data on the backend.
4.  **View**: The frontend fetches the new JSON reports and displays them.
