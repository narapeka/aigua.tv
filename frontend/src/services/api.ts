/**
 * API Client
 * Axios-based API client for backend communication
 */

import axios from 'axios'
import type {
  DryRunRequest,
  DryRunResponse,
  JobResult,
  TMDBSearchRequest,
  TMDBSearchResponse,
  ConfigData,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Jobs API
export const jobsApi = {
  startDryRun: async (request: DryRunRequest): Promise<DryRunResponse> => {
    const { data } = await api.post<DryRunResponse>('/jobs/dry-run', request)
    return data
  },

  getJobResult: async (jobId: string): Promise<JobResult> => {
    const { data } = await api.get<JobResult>(`/jobs/${jobId}`)
    return data
  },

  executeJob: async (jobId: string): Promise<{ status: string; job_id: string }> => {
    const { data} = await api.post(`/jobs/${jobId}/execute`)
    return data
  },

  updateShowSelection: async (
    jobId: string,
    showId: string,
    selected: boolean
  ): Promise<void> => {
    await api.put(`/jobs/${jobId}/shows/${showId}/select`, { selected })
  },

  updateSeasonSelection: async (
    jobId: string,
    showId: string,
    seasonNumber: number,
    selected: boolean
  ): Promise<void> => {
    await api.put(`/jobs/${jobId}/shows/${showId}/seasons/${seasonNumber}/select`, { selected })
  },

  updateShowCategory: async (
    jobId: string,
    showId: string,
    category: string
  ): Promise<void> => {
    await api.put(`/jobs/${jobId}/shows/${showId}/category`, { category })
  },

  deleteJob: async (jobId: string): Promise<void> => {
    await api.delete(`/jobs/${jobId}`)
  },
}

// TMDB API
export const tmdbApi = {
  search: async (request: TMDBSearchRequest): Promise<TMDBSearchResponse> => {
    const { data } = await api.post<TMDBSearchResponse>('/tmdb/search', request)
    return data
  },

  getShow: async (tmdbId: number): Promise<any> => {
    const { data } = await api.get(`/tmdb/show/${tmdbId}`)
    return data
  },
}

// Config API
export const configApi = {
  getConfig: async (): Promise<ConfigData> => {
    const { data } = await api.get<ConfigData>('/config')
    return data
  },

  updateConfig: async (config: Partial<ConfigData>): Promise<void> => {
    await api.put('/config', config)
  },

  getCategories: async (): Promise<any> => {
    const { data } = await api.get('/config/categories')
    return data
  },
}

export default api
