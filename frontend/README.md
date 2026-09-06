# ⚽ Footy Frontend

A retro-tactile football management dashboard built with React 19, TypeScript, Tailwind CSS 4, Material UI, React Query, Zustand, and Vite.

---

## 🌟 Main Features

* 📊 **Premier League Command Center (`Dashboard.tsx`)**: Live league standings, European qualification chips, and matchday simulation controls.
* 🎛️ **Dual Render Mode Toggles**: Instant switching between **3D Broadcast Video** (powered by Google Research Football) and **2D Fast Simulation**.
* 🎥 **Cinematic Broadcast Replay Player (`MatchVideoReplay.tsx`)**: Streams high-definition MP4 match highlights with floating TV scoreboards, real-time match clock, and goal celebration overlays.
* ⚡ **Cached Video Reuse**: Reuses a discovered recording without rerunning the simulation.
* 📐 **Interactive 2D Tactical Board (`FormationViewer.tsx`)**: Real pitch coordinate visualization for formations (`4-3-3`, `4-2-3-1`, `3-5-2`, `4-4-2`, `5-3-2`).
* 👤 **Player Profiles & Scouting (`PlayerDetail.tsx`)**: FM-style 5-axis attribute pentagon radar charts (Technical, Mental, Physical, Goalkeeping) and dynamic contract valuations.
* 💼 **Transfer Market & Youth Academy**: Scouting directory, transfer history logs, and youth talent pipelines.
* 🧠 **AI Manager & ML Benchmarks (`MlBenchmarks.tsx`)**: Performance graphs comparing trained PyTorch DQN agents against heuristic managers.

---

## 🛠️ Prerequisites

* **Node.js**: v18.0 or higher
* **npm**: v9.0 or higher
* **FastAPI Backend**: Running on `http://localhost:5001`

---

## 🚀 Installation & Setup

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Optionally create `frontend/.env` (there is currently no checked-in frontend `.env.example`):
   ```bash
   # Windows PowerShell
   Set-Content .env 'VITE_API_BASE_URL=http://localhost:5001'

   # Linux / macOS
   printf 'VITE_API_BASE_URL=http://localhost:5001\n' > .env
   ```
   Default `.env`:
   ```ini
   VITE_API_BASE_URL=http://localhost:5001
   ```

---

## 🏃 Running the Application

Start the Vite development server:
```bash
npm run dev
```
Open [http://localhost:5173/](http://localhost:5173/) in your browser.

---

## 🧪 Testing & Building

```bash
# Run unit and component tests
npm test

# Build production bundle
npm run build

# Preview production build locally
npm run preview
```

Verified on 6 September 2026: TypeScript compilation passed, the Vite production build completed (2,225 modules), and both Jest suites passed (6 tests). The API client currently reads its base URL when the module loads; changing the URL in the settings dialog does not reconfigure Axios. Simulation progress also depends on the backend returning a `run_id`, which is an open integration defect documented in [Current Status](../docs/05_current_status.md).
