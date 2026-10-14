import axios from 'axios';

const DEFAULT_API_BASE_URL = 'http://localhost:5001';
const API_BASE_URL = process.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
const API_TIMEOUT_MS = Number(process.env.VITE_API_TIMEOUT_MS || 30000);

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
});

export const resolveApiBaseUrl = (): string =>
  window.localStorage.getItem('footy_api_url')?.trim() || API_BASE_URL;

apiClient.interceptors.request.use((request) => {
  request.baseURL = resolveApiBaseUrl();
  return request;
});

export const resolveSimulationSocketUrl = (): string => {
  const socket = new URL(resolveApiBaseUrl());
  socket.protocol = socket.protocol === 'https:' ? 'wss:' : 'ws:';
  socket.pathname = '/ws';
  socket.search = '';
  socket.hash = '';
  return socket.toString();
};

export const resolveReplayVideoUrl = (url?: string | null): string => {
  if (!url) return '';
  if (/^(https?:|blob:)/.test(url)) return url;
  const base = window.localStorage.getItem('footy_api_url')?.trim() || API_BASE_URL;
  return `${base.replace(/\/+$/, '')}/${url.replace(/^\/+/, '')}`;
};

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
  assists_recorded?: boolean;
  minutes_played?: number;
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
  jersey_number?: number | null;
  overall_rating?: number | null;
  match_history?: { match_id: number; date: string; opponent: string; score: string; goals: number; minutes: number }[];
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
  const response = await apiClient.get<any>('/api/v1/teams');
  return Array.isArray(response.data) ? response.data : (response.data?.teams ?? []);
};

export const getPlayers = async (): Promise<Player[]> => {
  const response = await apiClient.get<any>('/api/v1/players');
  return Array.isArray(response.data) ? response.data : (response.data?.players ?? []);
};

export const runSimulation = async (params?: { seasons?: number; season_year?: number; render_mode?: '2d' | '3d' }) => {
  const response = await apiClient.post('/api/v1/run-simulation', params);
  return response.data; // { status: string, message: string, details?: string }
};

export const getAvailableSeasons = async (): Promise<number[]> => {
  const response = await apiClient.get<{ seasons: number[] }>('/api/v1/seasons');
  return response.data.seasons;
};

export const getSeasonReportData = async (year: number): Promise<SeasonReport | null> => {
  try {
    const response = await apiClient.get<SeasonReport>(`/api/v1/season-report/${year}`);
    return response.data;
  } catch (_error) {
    return null;
  }
};

export const getMatchesBySeason = async (seasonYear: number): Promise<any[]> => {
  const response = await apiClient.get(`/api/v1/seasons/${seasonYear}/matches`);
  return response.data.matches;
};

export const getMatchDetails = async (matchId: number | string): Promise<any> => {
  const response = await apiClient.get(`/api/v1/match/${matchId}`);
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
  const response = await apiClient.get<TeamHistoryResponse>(`/api/v1/team-history/${encodeURIComponent(teamName)}`);
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
  const response = await apiClient.get<FinancialSummaryResponse>('/api/v1/financial-summary');
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
  const response = await apiClient.get<YouthProspectsResponse>('/api/v1/youth-prospects');
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
  const response = await apiClient.get<TransferActivityResponse>('/api/v1/transfer-activity');
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
  const response = await apiClient.get<AllSeasonsOverviewResponse>('/api/v1/all-seasons-overview');
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
    elapsed_seconds?: number;
    episodes_per_policy?: number;
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

export interface MlModelItem {
  name: string;
  path: string;
  size_bytes: number;
  modified_at: string;
}

export const getMlReports = async (): Promise<MlReportListItem[]> => {
  const response = await apiClient.get<MlReportsResponse>('/api/v1/ml-reports');
  return response.data.reports;
};

export const getMlReport = async (reportName: string): Promise<MlReport> => {
  const response = await apiClient.get<MlReport>(`/api/v1/ml-reports/${encodeURIComponent(reportName)}`);
  return response.data;
};

export const getMlModels = async (): Promise<MlModelItem[]> => {
  const response = await apiClient.get<{ models: MlModelItem[] }>('/api/v1/ml-models');
  return response.data.models;
};

export const runMlEvaluation = async (params: {
  models: string[];
  episodes?: number;
  teams?: number;
  season_length?: number;
  fast_mode?: boolean;
  seed?: number;
}, onProgress?: (status: string) => void, signal?: AbortSignal): Promise<MlReport> => {
  const response = await apiClient.post<JobAcceptance>('/api/v1/run-ml-eval', params, { signal });
  window.sessionStorage.setItem('footy_ml_job', response.data.job_id);
  const job = await waitForJob(response.data.job_id, onProgress, signal);
  window.sessionStorage.removeItem('footy_ml_job');
  if (!job.result) throw new Error('Evaluation completed without a report');
  return job.result as unknown as MlReport;
};

export const resumeMlEvaluation = async (onProgress: (status: string) => void, signal?: AbortSignal): Promise<MlReport | null> => {
  const identity = window.sessionStorage.getItem('footy_ml_job');
  if (!identity) return null;
  try {
    const job = await waitForJob(identity, onProgress, signal);
    window.sessionStorage.removeItem('footy_ml_job');
    return job.result as unknown as MlReport;
  } catch (error) {
    if (!signal?.aborted) window.sessionStorage.removeItem('footy_ml_job');
    throw error;
  }
};

export interface JobAcceptance {
  status: string;
  message: string;
  job_id: string;
  run_id?: string;
  status_url: string;
}

export interface WorkJob {
  job_id: string;
  kind: string;
  run_id?: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted';
  error_message?: string;
  result?: Record<string, unknown>;
}

export const getJob = async (jobId: string, signal?: AbortSignal): Promise<WorkJob> =>
  (await apiClient.get<WorkJob>(`/api/v1/jobs/${encodeURIComponent(jobId)}`, { signal })).data;

export const cancelJob = async (jobId: string): Promise<WorkJob> =>
  (await apiClient.post<WorkJob>(`/api/v1/jobs/${encodeURIComponent(jobId)}/cancel`)).data;

export const waitForJob = async (jobId: string, onProgress?: (status: string) => void,
                                 signal?: AbortSignal): Promise<WorkJob> => {
  for (;;) {
    signal?.throwIfAborted();
    const job = await getJob(jobId, signal);
    onProgress?.(job.status);
    if (job.status === 'completed') return job;
    if (['failed', 'cancelled', 'interrupted'].includes(job.status)) {
      throw new Error(job.error_message || `Job ${job.status}`);
    }
    await new Promise<void>((resolve, reject) => {
      const abort = () => { clearTimeout(timer); reject(new DOMException('Polling cancelled', 'AbortError')); };
      const timer = setTimeout(() => { signal?.removeEventListener('abort', abort); resolve(); }, 1000);
      signal?.addEventListener('abort', abort, { once: true });
    });
  }
};

export const createSaveState = async (): Promise<{ status: string; save_id: string; message: string }> => {
  const response = await apiClient.post<{ status: string; save_id: string; message: string }>('/api/v1/saves');
  return response.data;
};

export const listSaveStates = async (): Promise<Array<{ save_id: string; timestamp: string; size_bytes: number }>> => {
  const response = await apiClient.get('/api/v1/saves');
  return response.data;
};

export interface EngineStatusResponse {
  engine_mode: string;
  grf_available: boolean;
  device: string;
  checkpoint_found: boolean;
  baller_dir: string;
  recordings_dir: string;
}

export interface MatchVideoResponse {
  match_id: string;
  video_url: string | null;
  size_bytes?: number;
  available: boolean;
  message?: string;
}

export interface GrfMatchSimulationRequest {
  match_id?: string;
  home_team_name: string;
  away_team_name: string;
  home_formation?: string;
  away_formation?: string;
  generate_video?: boolean;
  max_steps?: number;
  render_mode?: "3d" | "2d";
}

export interface GrfMatchSimulationResponse {
  match_id: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  possession: { home: number; away: number };
  shots: { home: number; away: number };
  xg: { home: number; away: number };
  timeline: Array<{
    minute: number;
    type: string;
    player: string;
    team: string;
    details: string;
  }>;
  video_url?: string | null;
}

export const getEngineStatus = async (): Promise<EngineStatusResponse> => {
  const response = await apiClient.get<EngineStatusResponse>('/api/v1/engine/status');
  return response.data;
};

export const getMatchVideo = async (matchId: string): Promise<MatchVideoResponse> => {
  const response = await apiClient.get<MatchVideoResponse>(`/api/v1/match/${matchId}/video`);
  return response.data;
};

export const simulateGrfMatch = async (params: GrfMatchSimulationRequest): Promise<GrfMatchSimulationResponse> => {
  const response = await apiClient.post<GrfMatchSimulationResponse>('/api/v1/match/simulate-grf', params);
  return response.data;
};

export interface MatchRenderStatusResponse {
  status: "idle" | "initializing" | "rendering" | "simulating" | "completed" | "failed" | "error";
  progress: number;
  step?: number;
  total_steps?: number;
  match_minute?: number;
  stage?: string;
  video_url?: string | null;
  score?: [number, number];
  completed: boolean;
  elapsed_seconds?: number;
  message?: string;
}

export const getMatchRenderStatus = async (matchId: string): Promise<MatchRenderStatusResponse> => {
  const response = await apiClient.get<MatchRenderStatusResponse>(`/api/v1/match/${matchId}/render-status`);
  return response.data;
};

export interface SimulationSettings {
  default_render_mode: "3d" | "2d";
  max_steps?: number;
  active_model?: string;
}

export const getSimulationSettings = async (): Promise<SimulationSettings> => {
  const response = await apiClient.get<SimulationSettings>('/api/v1/settings/simulation');
  return response.data;
};

export const updateSimulationSettings = async (settings: SimulationSettings): Promise<SimulationSettings> => {
  const response = await apiClient.post<SimulationSettings>('/api/v1/settings/simulation', settings);
  return response.data;
};

export interface CurrentSimulationRun {
  run_id: string;
  season_year: number;
  created_at: string | null;
  status: string;
  render_mode: "3d" | "2d";
  total_matches: number;
  matches_played: number;
  cancel_requested?: boolean;
  error_message?: string | null;
}

export const getCurrentSimulationRun = async (): Promise<CurrentSimulationRun> => {
  const response = await apiClient.get<CurrentSimulationRun>('/api/v1/simulation/current-run');
  return response.data;
};

export const getSimulationRun = async (runId: string): Promise<CurrentSimulationRun> =>
  (await apiClient.get<CurrentSimulationRun>(`/api/v1/simulation/runs/${encodeURIComponent(runId)}`)).data;

export interface SavedRun {
  run_id: string; season_year: number; created_at: string; status: string; matches_played: number; seasons: number[];
}
export interface CampaignSnapshot {
  run_id: string; season_year: number; matches_played: number;
  teams: Array<{ name: string; players: RetainedPlayer[]; finances: { budget: number } }>;
}
export interface RetainedPlayer {
  name: string; position: string; contract_length: number; wage: number;
  release_clause?: number | null;
  suspended_matches?: number;
  injury_days?: number;
  sell_on_clause?: { beneficiary: string; percentage: number } | null;
  loan_contract?: { owner: string; borrower: string; expires_day: number } | null;
}
export interface FinancialLedger {
  opening_balance: number; closing_balance: number; net_cashflow: number;
  entries: Array<{ entry_number: number; season_year: number; category: string; description: string; amount: number; balance: number }>;
}
export const getSimulationRuns = async (): Promise<SavedRun[]> =>
  (await apiClient.get<{ runs: SavedRun[] }>('/api/v1/simulation/runs')).data.runs;
export const getCampaignSnapshot = async (runId: string, year: number): Promise<CampaignSnapshot> =>
  (await apiClient.get<CampaignSnapshot>(`/api/v1/simulation/runs/${encodeURIComponent(runId)}/seasons/${year}`)).data;
export const getCampaignFinances = async (runId: string, club: string): Promise<FinancialLedger> =>
  (await apiClient.get<FinancialLedger>(`/api/v1/simulation/runs/${encodeURIComponent(runId)}/finances/${encodeURIComponent(club)}`)).data;

export interface TimelineSegment {
  segment_type: string;
  source_step_start: number;
  source_step_end: number;
  pts_start_seconds: number;
  pts_end_seconds: number;
  match_minute_start: number;
  match_minute_end: number;
  event_ids: string[];
}

export interface PresentationTimeline {
  match_id: string;
  fps: number;
  total_frames: number;
  total_duration_seconds: number;
  segments: TimelineSegment[];
  events_pts_map: Record<string, number>;
  minute_to_pts: Record<string, number>;
  timeline_version: string;
}

export const getMatchTimeline = async (matchId: string | number): Promise<PresentationTimeline | null> => {
  try {
    const response = await apiClient.get<PresentationTimeline>(`/api/v1/match/${matchId}/timeline`);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) return null;
    throw error;
  }
};

export interface MatchRenderResponse {
  match_id: string;
  status: string;
  video_url: string | null;
  render_mode_used?: string | null;
  message?: string | null;
}

export const renderMatchReplay = async (
  matchId: string | number,
  options?: { render_mode?: '3d' | '2d' | 'auto'; force?: boolean; resolution?: '720p' | '1080p'; theme?: 'dark' | 'light'; camera?: 'wide' | 'bird' | 'tele' | 'director' }
): Promise<MatchRenderResponse> => {
  const response = await apiClient.post<MatchRenderResponse>(`/api/v1/match/${matchId}/render`, options || {}, { timeout: 660000 });
  return response.data;
};

