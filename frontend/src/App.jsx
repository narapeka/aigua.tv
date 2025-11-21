import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useParams } from 'react-router-dom'
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Container, 
  Box, 
  Alert, 
  Paper,
  Button as MuiButton,
  Link as MuiLink,
  CircularProgress,
  Stack
} from '@mui/material'
import { Link } from 'react-router-dom'
import ConfigEditor from './components/ConfigEditor'
import FolderPicker from './components/FolderPicker'
import PreviewTable from './components/PreviewTable'
import ExecutionProgress from './components/ExecutionProgress'
import Button from './components/common/Button'
import { foldersApi, organizeApi, previewApi } from './services/api'

const SetupPage = () => {
  const [sourceFolder, setSourceFolder] = useState('')
  const [targetFolder, setTargetFolder] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const handleStartDryRun = async () => {
    if (!sourceFolder || !targetFolder) {
      setError('Please select both source and target folders')
      return
    }

    try {
      setLoading(true)
      setError(null)
      const response = await organizeApi.dryRun({
        source_folder: sourceFolder,
        target_folder: targetFolder,
      })
      navigate(`/preview/${response.data.job_id}`)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Setup Organization
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Paper sx={{ p: 3, mb: 3 }}>
          <FolderPicker
            label="Source Folder"
            value={sourceFolder}
            onChange={setSourceFolder}
            onBrowse={(path) => foldersApi.browse(path, sourceFolder)}
          />
        </Paper>

        <Paper sx={{ p: 3, mb: 3 }}>
          <FolderPicker
            label="Target Folder"
            value={targetFolder}
            onChange={setTargetFolder}
            onBrowse={(path) => foldersApi.browse(path, targetFolder)}
          />
        </Paper>

        <Stack direction="row" spacing={2}>
          <Button onClick={handleStartDryRun} disabled={loading}>
            {loading ? 'Starting...' : 'Start Dry Run'}
          </Button>
          <Button 
            onClick={() => navigate('/preview/mock')} 
            variant="secondary"
            disabled={loading}
          >
            Load Mock Preview (Test)
          </Button>
        </Stack>
      </Box>
    </Container>
  )
}

const PreviewPage = () => {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedFolders, setSelectedFolders] = useState(new Set())
  const [manualMatches, setManualMatches] = useState({})
  const [executing, setExecuting] = useState(false)

  React.useEffect(() => {
    // If jobId is "mock", load mock data instead
    if (jobId === 'mock') {
      loadMockPreview()
    } else {
      loadPreview()
      // Poll for preview data
      const interval = setInterval(loadPreview, 2000)
      return () => clearInterval(interval)
    }
  }, [jobId])

  const loadMockPreview = async () => {
    try {
      const response = await previewApi.get('mock')
      setPreview(response.data)
      setLoading(false)
      setError(null)
      // Initialize selected folders (all by default)
      if (response.data.shows && selectedFolders.size === 0) {
        const allSelected = new Set(response.data.shows.map((s) => s.folder_name))
        setSelectedFolders(allSelected)
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setLoading(false)
    }
  }

  const loadPreview = async () => {
    try {
      const response = await previewApi.get(jobId)
      setPreview(response.data)
      setLoading(false)
      setError(null)
      // Initialize selected folders (all by default)
      if (response.data.shows && selectedFolders.size === 0) {
        const allSelected = new Set(response.data.shows.map((s) => s.folder_name))
        setSelectedFolders(allSelected)
      }
    } catch (err) {
      // 400 means job not completed yet - keep polling silently
      if (err.response?.status === 400) {
        const errorMsg = err.response?.data?.detail || err.message
        // Check if it's just "not completed" vs actual error
        if (errorMsg && errorMsg.includes('not completed')) {
          // Still processing, don't show error
          return
        }
      }
      // Only show error for real errors (404, 500, etc.)
      if (err.response?.status !== 400) {
        setError(err.response?.data?.detail || err.message)
        setLoading(false)
      }
    }
  }

  const handleSelectionChange = (folderName, selected) => {
    const newSelected = new Set(selectedFolders)
    if (selected) {
      newSelected.add(folderName)
    } else {
      newSelected.delete(folderName)
    }
    setSelectedFolders(newSelected)
  }

  const handleManualMatch = (folderName, tmdbId) => {
    setManualMatches((prev) => ({ ...prev, [folderName]: tmdbId }))
  }

  const handleExecute = async () => {
    if (selectedFolders.size === 0) {
      setError('Please select at least one show to organize')
      return
    }

    try {
      setExecuting(true)
      setError(null)
      const response = await organizeApi.execute({
        job_id: jobId,
        selected_folders: Array.from(selectedFolders),
        manual_matches: Object.keys(manualMatches).length > 0 ? manualMatches : undefined,
      })
      navigate(`/execute/${response.data.job_id}`)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setExecuting(false)
    }
  }

  if (loading && !preview) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4, textAlign: 'center' }}>
          <CircularProgress sx={{ mb: 2 }} />
          <Typography variant="h6" gutterBottom>Loading preview...</Typography>
          <Typography variant="body2" color="text.secondary">
            This may take a few moments while we scan your folders and match shows with TMDB.
          </Typography>
        </Box>
      </Container>
    )
  }

  if (error && !preview) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Alert severity="error">{error}</Alert>
        </Box>
      </Container>
    )
  }

  if (!preview) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4, textAlign: 'center' }}>
          <CircularProgress sx={{ mb: 2 }} />
          <Typography variant="h6" gutterBottom>Waiting for preview data...</Typography>
          <Typography variant="body2" color="text.secondary">
            The dry-run is still processing. Please wait...
          </Typography>
        </Box>
      </Container>
    )
  }

  // Update shows with selection state
  const showsWithSelection = preview.shows.map((show) => ({
    ...show,
    selected: selectedFolders.has(show.folder_name),
  }))

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Preview
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ mb: 3 }}>
          <Typography variant="body1" gutterBottom>
            Selected: {selectedFolders.size} / {preview.shows.length} shows
          </Typography>
          {preview.stats && (
            <Typography variant="body2" color="text.secondary">
              Episodes: {preview.stats.episodes_moved || 0} | Seasons: {preview.stats.seasons_processed || 0}
            </Typography>
          )}
        </Box>

        <Paper sx={{ mb: 3 }}>
          <PreviewTable
            shows={showsWithSelection}
            onSelectionChange={handleSelectionChange}
            onManualMatch={handleManualMatch}
          />
        </Paper>

        <Stack direction="row" spacing={2}>
          <Button onClick={handleExecute} disabled={executing || selectedFolders.size === 0} variant="success">
            {executing ? 'Executing...' : 'Execute Organization'}
          </Button>
          <Button onClick={() => navigate('/')} variant="secondary">
            Back to Setup
          </Button>
        </Stack>
      </Box>
    </Container>
  )
}

const ExecutePage = () => {
  const { jobId } = useParams()
  const navigate = useNavigate()

  const handleCancel = async () => {
    try {
      await organizeApi.cancel(jobId)
      navigate('/')
    } catch (err) {
      console.error('Error cancelling job:', err)
    }
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <ExecutionProgress jobId={jobId} onCancel={handleCancel} />
        <Box sx={{ mt: 3 }}>
          <Button onClick={() => navigate('/')} variant="secondary">
            Back to Home
          </Button>
        </Box>
      </Box>
    </Container>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              <MuiLink component={Link} to="/" color="inherit" underline="none">
                TV Show Organizer
              </MuiLink>
            </Typography>
            <MuiLink component={Link} to="/config" color="inherit" underline="none" sx={{ mx: 2 }}>
              Configuration
            </MuiLink>
            <MuiLink component={Link} to="/setup" color="inherit" underline="none">
              Setup
            </MuiLink>
          </Toolbar>
        </AppBar>

        <Routes>
          <Route path="/" element={<SetupPage />} />
          <Route path="/config" element={<ConfigEditor />} />
          <Route path="/setup" element={<SetupPage />} />
          <Route path="/preview/:jobId" element={<PreviewPage />} />
          <Route path="/execute/:jobId" element={<ExecutePage />} />
        </Routes>
      </Box>
    </BrowserRouter>
  )
}

export default App

