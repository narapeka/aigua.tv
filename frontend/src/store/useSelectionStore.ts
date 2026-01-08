/**
 * Selection Store
 * Manages show/season/episode selection state
 */

import { create } from 'zustand'
import { jobsApi } from '../services/api'
import type { ShowData, SelectionStats } from '../types'

interface SelectionStore {
  // Local selection cache for performance
  localSelections: Map<string, boolean> // key: show_id, season_number, or episode_id

  // Actions
  toggleShow: (jobId: string, showId: string, currentState: boolean) => Promise<void>
  toggleSeason: (
    jobId: string,
    showId: string,
    seasonNumber: number,
    currentState: boolean
  ) => Promise<void>
  selectAll: (shows: ShowData[]) => void
  deselectAll: () => void
  getSelectionStats: (shows: ShowData[]) => SelectionStats
  clearSelections: () => void
}

export const useSelectionStore = create<SelectionStore>((set, get) => ({
  localSelections: new Map(),

  // Toggle show selection
  toggleShow: async (jobId: string, showId: string, currentState: boolean) => {
    const newState = !currentState

    // Update local state immediately for responsiveness
    get().localSelections.set(`show_${showId}`, newState)
    set({ localSelections: new Map(get().localSelections) })

    try {
      await jobsApi.updateShowSelection(jobId, showId, newState)
    } catch (error) {
      // Revert on error
      get().localSelections.delete(`show_${showId}`)
      set({ localSelections: new Map(get().localSelections) })
      throw error
    }
  },

  // Toggle season selection
  toggleSeason: async (
    jobId: string,
    showId: string,
    seasonNumber: number,
    currentState: boolean
  ) => {
    const newState = !currentState
    const key = `season_${showId}_${seasonNumber}`

    // Update local state
    get().localSelections.set(key, newState)
    set({ localSelections: new Map(get().localSelections) })

    try {
      await jobsApi.updateSeasonSelection(jobId, showId, seasonNumber, newState)
    } catch (error) {
      // Revert on error
      get().localSelections.delete(key)
      set({ localSelections: new Map(get().localSelections) })
      throw error
    }
  },

  // Select all
  selectAll: (shows: ShowData[]) => {
    const selections = new Map<string, boolean>()

    shows.forEach((show) => {
      selections.set(`show_${show.id}`, true)
      show.seasons.forEach((season) => {
        selections.set(`season_${show.id}_${season.season_number}`, true)
      })
    })

    set({ localSelections: selections })
  },

  // Deselect all
  deselectAll: () => {
    set({ localSelections: new Map() })
  },

  // Get selection statistics
  getSelectionStats: (shows: ShowData[]): SelectionStats => {
    let totalShows = shows.length
    let selectedShows = 0
    let totalEpisodes = 0
    let selectedEpisodes = 0

    shows.forEach((show) => {
      if (show.selected) {
        selectedShows++
      }

      show.seasons.forEach((season) => {
        totalEpisodes += season.episodes.length

        if (season.selected) {
          season.episodes.forEach((episode) => {
            if (episode.selected) {
              selectedEpisodes++
            }
          })
        }
      })
    })

    return {
      totalShows,
      selectedShows,
      totalEpisodes,
      selectedEpisodes,
    }
  },

  // Clear selections
  clearSelections: () => {
    set({ localSelections: new Map() })
  },
}))
