import axios from 'axios'

// V prohlížeči vždy používáme relativní URL - Vite proxy to přeposílá na backend
const apiClient = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
})

const getCredentials = (): string => {
  const username = localStorage.getItem('lol_username') ?? ''
  const password = localStorage.getItem('lol_password') ?? ''
  return btoa(`${username}:${password}`)
}

apiClient.interceptors.request.use((config) => {
  config.headers['Authorization'] = `Basic ${getCredentials()}`
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('lol_username')
      localStorage.removeItem('lol_password')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export interface Team {
  id: number
  pandascore_id: string
  name: string
  acronym: string | null
  image_url: string | null
  region: string | null
}

export interface League {
  id: number
  name: string
  slug: string | null
  region: string | null
  image_url: string | null
}

export interface Tournament {
  id: number
  name: string
  slug: string | null
  league: League | null
}

export interface Prediction {
  id: number
  win_prob_team1: number
  win_prob_team2: number
  predicted_total_kills: number | null
  predicted_duration_seconds: number | null
  confidence_score: number | null
  draft_adjusted: boolean
  created_at: string
}

export interface OddsSnapshot {
  id: number
  bookmaker: string
  team1_odds: number
  team2_odds: number
  implied_prob_team1: number
  implied_prob_team2: number
  vig: number | null
  snapshot_at: string
}

export interface Match {
  id: number
  pandascore_id: string
  team1: Team | null
  team2: Team | null
  scheduled_at: string | null
  status: string
  number_of_games: number | null
  tournament: Tournament | null
  latest_prediction: Prediction | null
  latest_odds: OddsSnapshot | null
  live_game_id: string | null
}

export interface MatchDetail extends Match {
  games: Game[]
  predictions: Prediction[]
  odds_snapshots: OddsSnapshot[]
  patch_version: string | null
  winner_id: number | null
}

export interface Game {
  id: number
  game_number: number
  status: string
  duration_seconds: number | null
  total_kills: number | null
  winner_id: number | null
  pandascore_id: string | null
  lol_esports_game_id: string | null
}

export const matchesApi = {
  getLive: (params?: { league_id?: number }) =>
    apiClient.get<Match[]>('/api/matches/live', { params }),

  getUpcoming: (params?: { league_id?: number; days_ahead?: number; with_odds_only?: boolean }) =>
    apiClient.get<Match[]>('/api/matches/upcoming', { params }),

  getFinished: (params?: { page?: number; per_page?: number; league_id?: number }) =>
    apiClient.get<Match[]>('/api/matches/finished', { params }),

  getById: (id: number) => apiClient.get<MatchDetail>(`/api/matches/${id}`),
}

export const teamsApi = {
  list: (params?: { region?: string; search?: string }) =>
    apiClient.get<Team[]>('/api/teams', { params }),
  getById: (id: number) => apiClient.get<Team>(`/api/teams/${id}`),
}

export const leaguesApi = {
  list: (params?: { region?: string; search?: string }) =>
    apiClient.get<League[]>('/api/leagues', { params }),
}

export const predictionsApi = {
  list: (params?: { match_id?: number; page?: number }) =>
    apiClient.get<Prediction[]>('/api/predictions', { params }),
  generate: (matchId: number) =>
    apiClient.post<Prediction>(`/api/predictions/${matchId}/generate`),
}

export const adminApi = {
  health: () => apiClient.get('/api/admin/health'),
  ingestionLogs: () => apiClient.get('/api/admin/ingestion-logs'),
  syncMatches: () => apiClient.post('/api/admin/sync/matches'),
  syncLeagues: () => apiClient.post('/api/admin/sync/leagues'),
  syncTeams: () => apiClient.post('/api/admin/sync/teams'),
}

export interface LiveSignals {
  gold_diff: number
  tower_diff: number
  baron_diff: number
  kill_diff: number
  dragon_diff: number
  inhibitor_diff: number
}

export interface LivePrediction {
  game_id: string
  win_prob_blue: number
  win_prob_red: number
  signals: LiveSignals
  blue_dragons: string[]
  red_dragons: string[]
  blue_total_kills: number
  red_total_kills: number
  blue_total_gold: number
  red_total_gold: number
  game_state: string
  frame_timestamp: string | null
  game_timer_seconds: number
  game_timer: string
  blue_towers: number
  red_towers: number
  blue_barons: number
  red_barons: number
}

export interface LiveWindow {
  game_id: string
  prediction: LivePrediction | null
  raw_participants_blue: Record<string, unknown>[]
  raw_participants_red: Record<string, unknown>[]
  game_state: string
  prob_history: number[]
  game_timer_seconds: number
}

export const liveApi = {
  getLivePrediction: (gameId: string) =>
    apiClient.get<LiveWindow>(`/api/live/${gameId}`),
}

export default apiClient