import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  LinearProgress,
  Card,
  CardContent,
  Alert,
  Button,
  List,
  ListItem,
  ListItemText,
} from '@mui/material'
import { Home, CheckCircle, Error } from '@mui/icons-material'
import { useJobStore } from '../store/useJobStore'

export default function ExecutePage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const { jobResult, status, fetchJobResult } = useJobStore()
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (jobId) {
      // Poll for status updates
      const interval = setInterval(() => {
        fetchJobResult(jobId)
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [jobId])

  useEffect(() => {
    if (jobResult && jobResult.stats) {
      const total = jobResult.stats.shows_processed || 0
      const completed = jobResult.stats.episodes_moved || 0
      setProgress(total > 0 ? (completed / total) * 100 : 0)
    }
  }, [jobResult])

  const isComplete = status === 'completed'
  const hasFailed = status === 'failed'

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>
        {isComplete ? 'Execution Complete!' : hasFailed ? 'Execution Failed' : 'Executing...'}
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          {!isComplete && !hasFailed && (
            <>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Progress
              </Typography>
              <LinearProgress
                variant={progress > 0 ? 'determinate' : 'indeterminate'}
                value={progress}
                sx={{ mb: 2, height: 10, borderRadius: 1 }}
              />
              <Typography variant="body2" align="center">
                {Math.round(progress)}%
              </Typography>
            </>
          )}

          {isComplete && (
            <Alert severity="success" icon={<CheckCircle />}>
              Organization completed successfully!
            </Alert>
          )}

          {hasFailed && (
            <Alert severity="error" icon={<Error />}>
              {jobResult?.error || 'Execution failed. Please check the logs.'}
            </Alert>
          )}
        </CardContent>
      </Card>

      {jobResult?.stats && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Statistics
            </Typography>
            <List dense>
              <ListItem>
                <ListItemText
                  primary="Shows Processed"
                  secondary={jobResult.stats.shows_processed || 0}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Episodes Moved"
                  secondary={jobResult.stats.episodes_moved || 0}
                />
              </ListItem>
              {jobResult.stats.errors > 0 && (
                <ListItem>
                  <ListItemText
                    primary="Errors"
                    secondary={jobResult.stats.errors}
                    secondaryTypographyProps={{ color: 'error' }}
                  />
                </ListItem>
              )}
            </List>
          </CardContent>
        </Card>
      )}

      {(isComplete || hasFailed) && (
        <Button
          fullWidth
          variant="contained"
          startIcon={<Home />}
          onClick={() => navigate('/')}
        >
          Return to Home
        </Button>
      )}
    </Box>
  )
}
