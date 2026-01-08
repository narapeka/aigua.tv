/**
 * TypeScript type definitions
 * Mirrors backend Pydantic models
 */

export enum JobStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export interface TMDBMetadata {
  id: number
  name: string
  original_name?: string
  year?: number
  match_confidence?: string
  genre_ids?: number[]
  origin_country?: string[]
  poster_path?: string
  overview?: string
}

export interface EpisodeData {
  episode_number: number
  original_file: string
  original_path: string
  new_file: string
  new_path: string
  status: string
  selected: boolean
  tmdb_title?: string
  error?: string
}

export interface SeasonData {
  season_number: number
  episodes: EpisodeData[]
  selected: boolean
  original_folder?: string
}

export interface ShowData {
  id: string
  name: string
  category?: string
  folder_type: string
  original_folder: string
  tmdb_metadata?: TMDBMetadata
  confidence: string
  seasons: SeasonData[]
  selected: boolean
  cn_name?: string
  en_name?: string
  year?: number
  tmdb_id?: number
}

export interface UnprocessedShow {
  folder_name: string
  reason: string
}

export interface JobResult {
  job_id: string
  status: JobStatus
  input_dir: string
  output_dir: string
  stats: Record<string, number>
  processed_shows: ShowData[]
  unprocessed_shows: Array<{ folder_name: string; reason: string }>
  created_at: string
  updated_at: string
  error?: string
}

export interface DryRunRequest {
  input_dir: string
  output_dir: string
  config_overrides?: Record<string, any>
}

export interface DryRunResponse {
  job_id: string
  status: JobStatus
}

export interface TMDBSearchRequest {
  query: string
  year?: number
}

export interface TMDBSearchResult {
  id: number
  name: string
  original_name: string
  first_air_date?: string
  overview?: string
  poster_path?: string
  vote_average?: number
  origin_country?: string[]
}

export interface TMDBSearchResponse {
  results: TMDBSearchResult[]
}

export interface ConfigData {
  llm: Record<string, any>
  tmdb: Record<string, any>
  proxy?: Record<string, any>
  category?: Record<string, any>
}

export interface ProgressMessage {
  type: 'progress' | 'log' | 'status' | 'completed' | 'error'
  data: Record<string, any>
}

export interface SelectionStats {
  totalShows: number
  selectedShows: number
  totalEpisodes: number
  selectedEpisodes: number
}
