import axios from 'axios'

// In development, use the proxy (relative path)
// In production, use the full API URL or relative path
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Config API
export const configApi = {
  get: () => api.get('/config'),
  update: (data) => api.put('/config', data),
  validate: () => api.get('/config/validate'),
}

// Folders API
export const foldersApi = {
  scan: (sourceFolder) => api.post('/folders/scan', { source_folder: sourceFolder }),
  browse: (path, base) => api.get('/folders/browse', { params: { path, base } }),
}

// TMDB API
export const tmdbApi = {
  search: (query, language) => api.post('/tmdb/search', { query, language }),
  getShow: (tmdbId) => api.get(`/tmdb/show/${tmdbId}`),
}

// Organize API
export const organizeApi = {
  dryRun: (data) => api.post('/organize/dry-run', data),
  execute: (data) => api.post('/organize/execute', data),
  getStatus: (jobId) => api.get(`/organize/status/${jobId}`),
  cancel: (jobId) => api.post(`/organize/cancel/${jobId}`),
  updateMatch: (folderName, tmdbId) => api.put(`/organize/match/${folderName}`, { tmdb_id: tmdbId }),
}

// Preview API
export const previewApi = {
  get: (jobId) => api.get(`/preview/${jobId}`),
}

export default api

