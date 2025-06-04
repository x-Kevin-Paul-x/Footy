import axios from 'axios';

const API_BASE_URL = 'http://localhost:5001'; // Our Flask API

export interface SeasonReport {
  season: number;
  champions: string;
  champions_manager: {
    name: string;
    experience: number;
    formation: string;
    transfer_success_rate: number;
    market_trends: any; // Define more strictly if possible
  };
  table: [string, Record<string, number | string>][];
  transfers: {
    total_transfers: number;
    biggest_spenders: [string, number][];
    most_active: [string, number][];
    all_completed_transfers: any[]; // Define more strictly
  };
  best_players: any[]; // Define more strictly
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

export interface PlayerAttributes {
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
}

export interface TeamDetail {
  name: string;
  budget: number;
  manager_formation: string;
  squad_strength: number;
  players: Player[];
  team_season_stats: Record<string, number | string>;
  team_transfer_history: any[]; // Define more strictly
}


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
