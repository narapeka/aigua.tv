import { useState, useEffect } from 'react'
import { organizeApi } from '../services/api'

export const useJobStatus = (jobId, interval = 2000) => {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!jobId) {
      setLoading(false)
      return
    }

    const fetchStatus = async () => {
      try {
        const response = await organizeApi.getStatus(jobId)
        setStatus(response.data)
        setLoading(false)
        
        // Stop polling if job is completed, failed, or cancelled
        if (['completed', 'failed', 'cancelled'].includes(response.data.status)) {
          return
        }
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }

    fetchStatus()
    const intervalId = setInterval(fetchStatus, interval)

    return () => clearInterval(intervalId)
  }, [jobId, interval])

  return { status, loading, error }
}

