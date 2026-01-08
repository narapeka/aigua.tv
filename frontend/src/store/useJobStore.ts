/**
 * Job Store
 * Manages job state and operations
 */

import { create } from 'zustand'
import { jobsApi } from '../services/api'
import type { JobResult, JobStatus, DryRunRequest } from '../types'

interface JobStore {
  // State
  jobId: string | null
  jobResult: JobResult | null
  status: JobStatus | null
  isLoading: boolean
  error: string | null

  // Actions
  startDryRun: (request: DryRunRequest) => Promise<string>
  fetchJobResult: (jobId: string) => Promise<void>
  executeJob: () => Promise<void>
  clearJob: () => void
  setError: (error: string | null) => void
}

export const useJobStore = create<JobStore>((set, get) => ({
  // Initial state
  jobId: null,
  jobResult: null,
  status: null,
  isLoading: false,
  error: null,

  // Start dry-run
  startDryRun: async (request: DryRunRequest) => {
    set({ isLoading: true, error: null })

    try {
      const response = await jobsApi.startDryRun(request)

      set({
        jobId: response.job_id,
        status: response.status,
        isLoading: false,
      })

      // Start polling for result
      const pollInterval = setInterval(async () => {
        const currentJobId = get().jobId
        if (!currentJobId) {
          clearInterval(pollInterval)
          return
        }

        try {
          await get().fetchJobResult(currentJobId)

          const currentStatus = get().status
          if (currentStatus === 'completed' || currentStatus === 'failed') {
            clearInterval(pollInterval)
          }
        } catch (error) {
          clearInterval(pollInterval)
        }
      }, 2000)

      return response.job_id
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || error.message || 'Failed to start dry-run',
        isLoading: false,
      })
      throw error
    }
  },

  // Fetch job result
  fetchJobResult: async (jobId: string) => {
    try {
      const result = await jobsApi.getJobResult(jobId)

      set({
        jobResult: result,
        status: result.status,
        error: result.error || null,
      })
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || error.message || 'Failed to fetch job result',
      })
      throw error
    }
  },

  // Execute job
  executeJob: async () => {
    const { jobId } = get()
    if (!jobId) {
      throw new Error('No job ID available')
    }

    set({ isLoading: true, error: null })

    try {
      await jobsApi.executeJob(jobId)

      set({
        status: 'running',
        isLoading: false,
      })

      // Start polling for completion
      const pollInterval = setInterval(async () => {
        try {
          await get().fetchJobResult(jobId)

          const currentStatus = get().status
          if (currentStatus === 'completed' || currentStatus === 'failed') {
            clearInterval(pollInterval)
          }
        } catch (error) {
          clearInterval(pollInterval)
        }
      }, 2000)
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || error.message || 'Failed to execute job',
        isLoading: false,
      })
      throw error
    }
  },

  // Clear job
  clearJob: () => {
    set({
      jobId: null,
      jobResult: null,
      status: null,
      isLoading: false,
      error: null,
    })
  },

  // Set error
  setError: (error: string | null) => {
    set({ error })
  },
}))
