import React from 'react'
import { Box, Typography, Paper, Alert, CircularProgress, Stack } from '@mui/material'
import { useJobStatus } from '../hooks/useJobStatus'
import Button from './common/Button'

const ExecutionProgress = ({ jobId, onCancel }) => {
  const { status, loading, error } = useJobStatus(jobId)

  if (loading && !status) {
    return (
      <Box sx={{ py: 4, textAlign: 'center' }}>
        <CircularProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>Loading job status...</Typography>
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error">Error: {error}</Alert>
    )
  }

  if (!status) {
    return null
  }

  const getStatusSeverity = () => {
    switch (status.status) {
      case 'completed':
        return 'success'
      case 'failed':
        return 'error'
      case 'cancelled':
        return 'warning'
      case 'running':
        return 'info'
      default:
        return 'info'
    }
  }

  return (
    <Box>
      <Typography variant="h5" component="h2" gutterBottom>
        Execution Progress
      </Typography>

      <Box sx={{ mb: 3 }}>
        <Alert severity={getStatusSeverity()} sx={{ mb: 2 }}>
          <Typography variant="body1" sx={{ textTransform: 'capitalize', fontWeight: 500 }}>
            {status.status}
          </Typography>
        </Alert>

        {status.progress && (
          <Box sx={{ mt: 2 }}>
            {Object.entries(status.progress).map(([key, value]) => (
              <Typography key={key} variant="body2" sx={{ mb: 1 }}>
                {key}: {value}
              </Typography>
            ))}
          </Box>
        )}

        {status.error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            Error: {status.error}
          </Alert>
        )}

        {status.result && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Results
            </Typography>
            <Paper sx={{ p: 2, mt: 1 }}>
              {status.result.stats && (
                <Stack spacing={1}>
                  <Typography variant="body2">
                    Shows Processed: {status.result.stats.shows_processed || 0}
                  </Typography>
                  <Typography variant="body2">
                    Seasons Processed: {status.result.stats.seasons_processed || 0}
                  </Typography>
                  <Typography variant="body2">
                    Episodes Moved: {status.result.stats.episodes_moved || 0}
                  </Typography>
                  <Typography variant="body2">
                    Errors: {status.result.stats.errors || 0}
                  </Typography>
                </Stack>
              )}
            </Paper>
          </Box>
        )}
      </Box>

      {status.status === 'running' && (
        <Button onClick={onCancel} variant="danger">
          Cancel
        </Button>
      )}
    </Box>
  )
}

export default ExecutionProgress

