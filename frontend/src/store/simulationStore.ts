import { create } from 'zustand';
import type { SeasonReport } from '../services/api'; // Type-only import
import { getAvailableSeasons, getSeasonReportData, runSimulation as apiRunSimulation } from '../services/api';


interface SimulationState {
  availableSeasons: number[];
  selectedSeason: number | null;
  currentReport: SeasonReport | null;
  isLoading: boolean;
  isSimulating: boolean;
  error: string | null;
  simulationMessage: string | null;

  fetchAvailableSeasons: () => Promise<void>;
  selectSeason: (season: number | null) => Promise<void>;
  runSimulation: () => Promise<void>;
}

export const useSimulationStore = create<SimulationState>((set, get) => ({
  availableSeasons: [],
  selectedSeason: null,
  currentReport: null,
  isLoading: false,
  isSimulating: false,
  error: null,
  simulationMessage: null,

  fetchAvailableSeasons: async () => {
    set({ isLoading: true, error: null });
    try {
      const seasons = await getAvailableSeasons();
      set({ availableSeasons: seasons, isLoading: false });
      if (seasons.length > 0 && !get().selectedSeason) {
        // Auto-select the latest season if none is selected
        await get().selectSeason(seasons[0]);
      } else if (seasons.length === 0) {
        set({ selectedSeason: null, currentReport: null });
      }
    } catch (err) {
      set({ error: 'Failed to fetch available seasons.', isLoading: false });
      console.error(err);
    }
  },

  selectSeason: async (season) => {
    if (season === null) {
      set({ selectedSeason: null, currentReport: null, error: null });
      return;
    }
    set({ isLoading: true, error: null, selectedSeason: season });
    try {
      const report = await getSeasonReportData(season);
      set({ currentReport: report, isLoading: false });
    } catch (err) {
      set({ error: `Failed to fetch report for season ${season}.`, isLoading: false, currentReport: null });
      console.error(err);
    }
  },

  runSimulation: async () => {
    set({ isSimulating: true, error: null, simulationMessage: 'Simulation in progress...' });
    try {
      const result = await apiRunSimulation();
      set({ isSimulating: false, simulationMessage: result.message });
      if (result.status === 'success') {
        // Refresh available seasons and select the new latest one
        await get().fetchAvailableSeasons(); 
      } else {
        set({ error: result.message || 'Simulation failed.' });
      }
    } catch (err: any) {
      let errorMessage = 'An error occurred during simulation.';
      if (err.response && err.response.data && err.response.data.message) {
        errorMessage = err.response.data.message;
        if (err.response.data.details) {
          errorMessage += ` Details: ${err.response.data.details}`;
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      set({ error: errorMessage, isSimulating: false, simulationMessage: null });
      console.error(err);
    }
  },
}));
