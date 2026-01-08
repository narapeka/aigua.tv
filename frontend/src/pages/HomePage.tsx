import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Link,
} from '@mui/material'
import { PlayArrow, Settings } from '@mui/icons-material'
import { useJobStore } from '../store/useJobStore'

export default function HomePage() {
  const navigate = useNavigate()
  const { startDryRun, isLoading, error } = useJobStore()

  const [inputDir, setInputDir] = useState('')
  const [outputDir, setOutputDir] = useState('')

  const handleStartDryRun = async () => {
    if (!inputDir || !outputDir) {
      return
    }

    try {
      const jobId = await startDryRun({
        input_dir: inputDir,
        output_dir: outputDir,
      })

      // Navigate to review page
      navigate(`/review/${jobId}`)
    } catch (error) {
      console.error('Failed to start dry-run:', error)
    }
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', mt: 8 }}>
      <Typography variant="h3" gutterBottom align="center">
        TV Show Organizer
      </Typography>

      <Typography variant="body1" color="text.secondary" align="center" paragraph>
        Organize your TV show library with AI-powered name detection and TMDB metadata
      </Typography>

      <Card sx={{ mt: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Start Organization
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <TextField
            fullWidth
            label="Input Directory"
            placeholder="/path/to/tv/shows"
            value={inputDir}
            onChange={(e) => setInputDir(e.target.value)}
            margin="normal"
            helperText="Directory containing TV show folders"
          />

          <TextField
            fullWidth
            label="Output Directory"
            placeholder="/path/to/organized"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
            margin="normal"
            helperText="Where to organize the shows"
          />

          <Button
            fullWidth
            variant="contained"
            size="large"
            startIcon={isLoading ? <CircularProgress size={20} /> : <PlayArrow />}
            onClick={handleStartDryRun}
            disabled={!inputDir || !outputDir || isLoading}
            sx={{ mt: 3 }}
          >
            {isLoading ? 'Starting Dry-Run...' : 'Start Dry-Run'}
          </Button>

          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Link
              href="/config"
              underline="hover"
              sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}
            >
              <Settings fontSize="small" />
              Configuration
            </Link>
          </Box>
        </CardContent>
      </Card>

      <Box sx={{ mt: 4, p: 3, bgcolor: 'info.light', borderRadius: 1 }}>
        <Typography variant="subtitle2" gutterBottom>
          How it works:
        </Typography>
        <Typography variant="body2" component="ul" sx={{ pl: 2 }}>
          <li>Dry-run scans your TV shows and creates an organization plan</li>
          <li>Review the results and select what you want to organize</li>
          <li>Execute to move files to the target structure</li>
          <li>No files are moved during dry-run - it's completely safe!</li>
        </Typography>
      </Box>
    </Box>
  )
}
