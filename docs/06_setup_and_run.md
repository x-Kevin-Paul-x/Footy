# 06. Setup and Run Guide

Follow these instructions to set up the development environment and run the Footy Project.

## Prerequisites

*   **Python 3.8+**
*   **Node.js 16+** & **npm**

## 1. Backend Setup

1.  Navigate to the root directory.
2.  Install the required Python packages:
    ```bash
    pip install numpy names flask flask-cors
    ```

### Running the Simulation (Standalone)
To run the simulation without the UI (useful for testing logic):
```bash
python3 main.py
```
This will:
*   Reset the database (`football_sim.db`).
*   Simulate the configured number of seasons (default: 2).
*   Generate report files in `season_reports/`.

### Running the API
To serve data to the frontend:
```bash
python3 api.py
```
The API will start on `http://localhost:5001`.

## 2. Frontend Setup

1.  Navigate to the `frontend/` directory:
    ```bash
    cd frontend
    ```
2.  Install Node dependencies:
    ```bash
    npm install
    ```

### Running the Frontend
Start the development server:
```bash
npm run dev
```
Access the application at `http://localhost:5173`.

## 3. Running the Full System

1.  **Terminal 1 (API)**:
    ```bash
    python3 api.py
    ```
2.  **Terminal 2 (Frontend)**:
    ```bash
    cd frontend
    npm run dev
    ```
3.  Open your browser to the local URL provided by Vite (usually `http://localhost:5173`).
4.  In the Dashboard, look for a "Run Simulation" button to trigger `main.py` via the API, or simply view the data if you ran `main.py` manually beforehand.

## Troubleshooting

*   **Missing Dependencies**: If Python complains about missing modules, ensure you installed them: `names`, `numpy`, `flask`, `flask-cors`.
*   **Port Conflicts**:
    *   API uses port **5001**. Ensure it's free.
    *   Frontend uses port **5173** (default Vite).
*   **Database Errors**: If the database seems corrupted or schemas change, delete `football_sim.db` and run `main.py` to regenerate it.
