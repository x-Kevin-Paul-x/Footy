import axios from 'axios';

const API_BASE_URL = 'http://localhost:5001'; // Our Flask API

export interface Manager {
  name: string;
  experience: number;
  formation: string;
  transfer_success_rate: number;
  market_trends: any; // Define more strictly if possible
  team: string; // Added team property
  // Add other manager-specific details if available from backend
}

export interface Coach {
  name: string;
  specialty: string;
  experience_level: number;
  // Add other coach-specific details if available from backend
  learning_rate?: number;
  exploration_rate?: number;
  improvement_history?: Record<string, any[]>;
  training_effectiveness?: Record<string, number>;
  training_methods?: Record<string, Record<string, number>>;
  session_results?: any[];
  player_progress?: Record<string, Record<string, any[]>>;
}

export interface Physio {
  name: string;
  specialty?: string; // e.g., "Sports Medicine", "Rehabilitation"
  experience_level?: number;
  // Add other physio-specific details if available from backend
}

export interface SeasonReport {
  season_year: number;
  champions: string;
  champions_manager: Manager; // Use the new Manager interface
  table: [string, Record<string, number | string>][];
  transfers: {
    total_transfers: number;
    biggest_spenders: [string, number][];
    most_active: [string, number][];
    all_completed_transfers: any[]; // Define more strictly
  };
  best_players: Player[];
  season_stats: {
    total_matches: number;
    total_goals: number;
    average_goals_per_match: number;
    best_attack: [string, { gf: number }];
    best_defense: [string, { ga: number }];
  };
  all_teams_details: TeamDetail[];
}

export interface PlayerAttribute {
  [key: string]: number;
}

// Allow string indexing for PlayerAttributes
export interface PlayerAttributes {
  [key: string]: PlayerAttribute;
  pace: PlayerAttribute;
  shooting: PlayerAttribute;
  passing: PlayerAttribute;
  dribbling: PlayerAttribute;
  defending: PlayerAttribute;
  physical: PlayerAttribute;
  goalkeeping: PlayerAttribute;
}

export interface PlayerStats {
  goals: number;
  assists: number;
  appearances: number;
  fitness: number;
  clean_sheets: number;
  yellow_cards: number;
  red_cards: number;
  development?: { attribute: string; from: number; to: number; age: number }[];
}

export interface Player {
  name: string;
  age: number;
  position: string;
  team: string;
  potential: number;
  wage: number;
  contract_length: number;
  form: number[];
  injury_history: any[]; // Define more strictly if possible
  squad_role: string;
  attributes: PlayerAttributes;
  stats: PlayerStats;
  market_value: number;
  is_injured: boolean; // Added missing property
  injury_type: string | null; // Added missing property
  recovery_time: number; // Added missing property
}

export interface FinancialSummary {
  annual_revenue: number;
  annual_expenses: number;
  financial_health: string;
}

export interface TeamDetail {
  name: string;
  manager_name: string;
  manager_formation: string;
  budget: number;
  squad_strength: number;
  players: Player[];
  financial_summary: FinancialSummary;
  team_season_stats: Record<string, number>;
  // Add other properties as returned by backend if needed
}

export interface Team {
  name: string;
  budget: number;
  manager_name: string;
  squad_strength: number;
  // Add other properties as returned by /teams endpoint
}

export interface Player {
  name: string;
  age: number;
  position: string;
  team: string;
  potential: number;
  wage: number;
  contract_length: number;
  form: number[];
  injury_history: any[]; // Define more strictly if possible
  squad_role: string;
  attributes: PlayerAttributes;
  stats: PlayerStats;
  market_value: number;
  is_injured: boolean;
  injury_type: string | null;
  recovery_time: number;
}



export const getTeams = async (): Promise<Team[]> => {
  const response = await axios.get<Team[]>(`${API_BASE_URL}/teams`);
  return response.data;
};

export const getPlayers = async (): Promise<Player[]> => {
  const response = await axios.get<Player[]>(`${API_BASE_URL}/players`);
  return response.data;
};

export const runSimulation = async () => {
  const response = await axios.post(`${API_BASE_URL}/run-simulation`);
  return response.data; // { status: string, message: string, details?: string }
};

export const getAvailableSeasons = async (): Promise<number[]> => {
  const response = await axios.get<{ seasons: number[] }>(`${API_BASE_URL}/get-seasons`);
  return response.data.seasons;
};

export const getSeasonReportData = async (year: number): Promise<SeasonReport> => {
  const response = await axios.get<SeasonReport>(`${API_BASE_URL}/get-season-report/${year}`);
  return response.data;
};

// Fetch manager details from a single season report (current season)
export const getManagerDetails = async (managerName: string, season?: number): Promise<Manager> => {
  // If season is not provided, use the latest available season
  const seasonsResponse = await axios.get<{ seasons: number[] }>(`${API_BASE_URL}/get-seasons`);
  const seasons = seasonsResponse.data.seasons;
  const targetSeason = season ?? Math.max(...seasons);

  const reportResponse = await axios.get<SeasonReport>(`${API_BASE_URL}/get-season-report/${targetSeason}`);
  const report = reportResponse.data;

  // Try to find manager in champions_manager
  if (report.champions_manager && report.champions_manager.name === managerName) {
    return report.champions_manager;
  }

  // Try to find manager in all_teams_details
  for (const team of report.all_teams_details) {
    if (team.manager_name === managerName) {
      return {
        name: team.manager_name,
        experience: 0, // Placeholder - actual experience not in TeamDetail
        formation: team.manager_formation,
        transfer_success_rate: 0, // Placeholder - actual rate not in TeamDetail
        market_trends: {}, // Placeholder
        team: team.name, // Populate team name
      };
    }
  }

  // Fallback if manager not found
  return {
    name: managerName,
    experience: 0,
    formation: "N/A",
    transfer_success_rate: 0,
    market_trends: {},
    team: "N/A", // Fallback team name
  };
};

// Placeholder for fetching coach details
export const getCoachDetails = async (coachName: string): Promise<Coach> => {
  // This would ideally fetch from a dedicated backend endpoint
  // For now, return a dummy object
  return {
    name: coachName,
    specialty: "Tactics", // Placeholder
    experience_level: 5, // Placeholder
  };
};

// Placeholder for fetching physio details
export const getPhysioDetails = async (physioName: string): Promise<Physio> => {
  // This would ideally fetch from a dedicated backend endpoint
  // For now, return a dummy object
  return {
    name: physioName,
    specialty: "Sports Injury", // Placeholder
    experience_level: 4, // Placeholder
  };
};
