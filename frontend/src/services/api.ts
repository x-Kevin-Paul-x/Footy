import axios from 'axios';

const DEFAULT_API_BASE_URL = 'http://localhost:5001';
const API_BASE_URL = process.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
const API_TIMEOUT_MS = Number(process.env.VITE_API_TIMEOUT_MS || 30000);

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
});

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
  id?: string | number;
  name: string;
  crest?: string | null;
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
  const response = await apiClient.get<any>('/teams');
  return Array.isArray(response.data) ? response.data : (response.data?.teams ?? []);
};

export const getPlayers = async (): Promise<Player[]> => {
  const response = await apiClient.get<any>('/players');
  return Array.isArray(response.data) ? response.data : (response.data?.players ?? []);
};

export const runSimulation = async () => {
  const response = await apiClient.post('/run-simulation');
  return response.data; // { status: string, message: string, details?: string }
};

export const getAvailableSeasons = async (): Promise<number[]> => {
  const response = await apiClient.get<{ seasons: number[] }>('/get-seasons');
  return response.data.seasons;
};

export const getSeasonReportData = async (year: number): Promise<SeasonReport | null> => {
  try {
    const response = await apiClient.get<SeasonReport>(`/get-season-report/${year}`);
    return response.data;
  } catch (error) {
    return null;
  }
};

export const getMatchesBySeason = async (seasonYear: number): Promise<any[]> => {
  const response = await apiClient.get(`/matches/${seasonYear}`);
  return response.data.matches;
};

export const getMatchDetails = async (matchId: number): Promise<any> => {
  const response = await apiClient.get(`/match/${matchId}`);
  return response.data;
};

// Fetch manager details from a single season report (current season)
export const getManagerDetails = async (managerName: string, season?: number): Promise<Manager> => {
  // If season is not provided, use the latest available season
  const seasonsResponse = await apiClient.get<{ seasons: number[] }>('/get-seasons');
  const seasons = seasonsResponse.data.seasons;
  const targetSeason = season ?? Math.max(...seasons);

  const reportResponse = await apiClient.get<SeasonReport>(`/get-season-report/${targetSeason}`);
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

// New API functions for enhanced dashboard

export interface TeamHistoryEntry {
  season: number;
  position: number;
  points: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
}

export interface TeamHistoryResponse {
  history: TeamHistoryEntry[];
  team_name: string;
}

export const getTeamHistory = async (teamName: string): Promise<TeamHistoryResponse> => {
  const response = await apiClient.get<TeamHistoryResponse>(`/team-history/${encodeURIComponent(teamName)}`);
  return response.data;
};

export interface FinancialSummaryResponse {
  season: number;
  league_totals: {
    total_budget: number;
    average_budget: number;
    total_revenue: number;
    total_expenses: number;
    net_position: number;
  };
  health_distribution: Record<string, number>;
  top_5_richest: any[];
  bottom_5: any[];
}

export const getFinancialSummary = async (): Promise<FinancialSummaryResponse> => {
  const response = await apiClient.get<FinancialSummaryResponse>('/financial-summary');
  return response.data;
};

export interface YouthProspect {
  name: string;
  team: string;
  age: number;
  position: string;
  potential: number;
  current_rating: number;
}

export interface YouthProspectsResponse {
  prospects: YouthProspect[];
  total_youth: number;
}

export const getYouthProspects = async (): Promise<YouthProspectsResponse> => {
  const response = await apiClient.get<YouthProspectsResponse>('/youth-prospects');
  return response.data;
};

export interface TransferActivityResponse {
  transfers?: any[];
  top_transfers?: any[];
  total_completed?: number;
  total_value?: number;
  loans_completed?: number;
  summary?: {
    total_transfers: number;
    total_volume: number;
  };
}

export const getTransferActivity = async (): Promise<TransferActivityResponse> => {
  const response = await apiClient.get<TransferActivityResponse>('/transfer-activity');
  return response.data;
};

// All Seasons Overview Types
export interface SeasonSummary {
  season_year: number;
  champions: string;
  champion_points: number;
  top_scorer: {
    name: string;
    team: string;
    goals: number;
  } | null;
  total_goals: number;
  total_matches: number;
  avg_goals_per_match: number;
  best_attack: {
    team: string;
    goals: number;
  };
  best_defense: {
    team: string;
    goals_conceded: number;
  };
  transfers_completed: number;
  total_market_value: number;
}

export interface TeamPositionEntry {
  season: number;
  position: number;
  points: number;
}

export interface AllSeasonsOverviewResponse {
  seasons: SeasonSummary[];
  team_position_trends: Record<string, TeamPositionEntry[]>;
  total_seasons: number;
}

export const getAllSeasonsOverview = async (): Promise<AllSeasonsOverviewResponse> => {
  const response = await apiClient.get<AllSeasonsOverviewResponse>('/all-seasons-overview');
  return response.data;
};

export interface MlReportListItem {
  file_name: string;
  report_type: string;
  generated_at?: string;
  primary_policy?: string;
  best_policy_by_reward?: string;
  best_policy_by_points?: string;
  best_policy_by_position?: string;
  policy_count: number;
  config: Record<string, unknown>;
}

export interface MlPolicySummary {
  policy_name: string;
  episodes: number;
  avg_reward: number;
  std_reward: number;
  median_reward: number;
  best_reward: number;
  worst_reward: number;
  avg_position: number;
  std_position: number;
  median_position: number;
  best_position: number;
  worst_position: number;
  avg_points: number;
  std_points: number;
  median_points: number;
  avg_budget: number;
  avg_squad_size: number;
  avg_action_count: number;
  title_rate: number;
  top_4_rate: number;
  top_half_rate: number;
  action_distribution: Record<string, number>;
  action_share: Record<string, number>;
  position_histogram: Record<string, number>;
}

export interface MlPolicyComparison {
  reward_delta: number;
  points_delta: number;
  position_delta: number;
  top_4_rate_delta: number;
  title_rate_delta: number;
  budget_delta: number;
  squad_size_delta: number;
}

export interface MlReportSummary {
  primary_policy: string;
  best_policy_by_reward: string;
  best_policy_by_points: string;
  best_policy_by_position: string;
  reward_ranking?: Array<Record<string, number | string>>;
  points_ranking?: Array<Record<string, number | string>>;
  position_ranking?: Array<Record<string, number | string>>;
}

export interface MlReport {
  generated_at: string;
  report_name: string;
  report_type: string;
  config: Record<string, unknown>;
  runtime?: {
    warnings?: Record<string, string>;
    packages?: Record<string, string>;
  };
  model?: Record<string, unknown>;
  policy_models?: Record<string, Record<string, unknown>>;
  policies: Record<string, MlPolicySummary>;
  comparisons: Record<string, MlPolicyComparison>;
  summary: MlReportSummary;
}

export interface MlReportsResponse {
  reports: MlReportListItem[];
}

export const getMlReports = async (): Promise<MlReportListItem[]> => {
  const response = await apiClient.get<MlReportsResponse>('/ml-reports');
  return response.data.reports;
};

export const getMlReport = async (reportName: string): Promise<MlReport> => {
  const response = await apiClient.get<MlReport>(`/ml-reports/${encodeURIComponent(reportName)}`);
  return response.data;
};

