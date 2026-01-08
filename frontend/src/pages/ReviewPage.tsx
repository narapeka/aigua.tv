import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Chip,
  List,
  ListItem,
  ListItemText,
  Checkbox,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material'
import { ExpandMore, PlayArrow, Refresh } from '@mui/icons-material'
import { useJobStore } from '../store/useJobStore'
import { useSelectionStore } from '../store/useSelectionStore'

export default function ReviewPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const { jobResult, status, isLoading, error, fetchJobResult, executeJob } = useJobStore()
  const { getSelectionStats } = useSelectionStore()

  useEffect(() => {
    if (jobId) {
      fetchJobResult(jobId)
    }
  }, [jobId])

  const handleExecute = async () => {
    try {
      await executeJob()
      navigate(`/execute/${jobId}`)
    } catch (error) {
      console.error('Failed to execute:', error)
    }
  }

  if (isLoading || status === 'pending' || status === 'running') {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mt: 8 }}>
        <CircularProgress size={60} />
        <Typography sx={{ mt: 2 }}>Processing... Please wait</Typography>
        <Typography variant="body2" color="text.secondary">
          Scanning shows, extracting names, and fetching metadata
        </Typography>
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 4 }}>
        {error}
      </Alert>
    )
  }

  if (!jobResult) {
    return (
      <Alert severity="warning" sx={{ mt: 4 }}>
        Job not found or expired
      </Alert>
    )
  }

  const stats = getSelectionStats(jobResult.processed_shows)

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Review Results</Typography>
        <Button
          variant="contained"
          size="large"
          startIcon={<PlayArrow />}
          onClick={handleExecute}
          disabled={stats.selectedEpisodes === 0}
        >
          Execute Selected ({stats.selectedEpisodes} episodes)
        </Button>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 3 }}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Shows
              </Typography>
              <Typography variant="h6">
                {stats.selectedShows} / {stats.totalShows}
              </Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Episodes
              </Typography>
              <Typography variant="h6">
                {stats.selectedEpisodes} / {stats.totalEpisodes}
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {jobResult.unprocessed_shows.length > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {jobResult.unprocessed_shows.length} shows skipped (low confidence or no TMDB match)
        </Alert>
      )}

      <List>
        {jobResult.processed_shows.map((show) => (
          <Card key={show.id} sx={{ mb: 2 }}>
            <Accordion defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                  <Checkbox checked={show.selected} />
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="h6">{show.name}</Typography>
                    <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                      <Chip label={show.confidence} size="small" color="primary" />
                      {show.category && <Chip label={show.category} size="small" />}
                      <Chip
                        label={`${show.seasons.length} seasons`}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  </Box>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <List dense>
                  {show.seasons.map((season) => (
                    <ListItem key={season.season_number}>
                      <Checkbox checked={season.selected} size="small" />
                      <ListItemText
                        primary={`Season ${season.season_number}`}
                        secondary={`${season.episodes.filter((e) => e.selected).length} / ${season.episodes.length} episodes`}
                      />
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          </Card>
        ))}
      </List>
    </Box>
  )
}
