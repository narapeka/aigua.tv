import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Stack,
  List,
  ListItem,
  ListItemButton,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material'
import { tmdbApi } from '../services/api'
import Button from './common/Button'
import Input from './common/Input'

const TMDBSearchModal = ({ isOpen, onClose, onSelect, folderName }) => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSearch = async () => {
    if (!query.trim()) return

    try {
      setLoading(true)
      setError(null)
      const response = await tmdbApi.search(query)
      setResults(response.data.results || [])
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (show) => {
    onSelect(show.id)
    onClose()
  }

  return (
    <Dialog open={isOpen} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Search TMDB for {folderName}</DialogTitle>
      <DialogContent>
        <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
          <Box sx={{ flexGrow: 1 }}>
            <Input
              value={query}
              onChange={setQuery}
              placeholder="Enter show name..."
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
          </Box>
          <Button onClick={handleSearch} disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </Button>
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress />
          </Box>
        )}

        {!loading && results.length > 0 && (
          <List sx={{ maxHeight: 400, overflow: 'auto' }}>
            {results.map((show) => (
              <ListItem key={show.id} disablePadding>
                <ListItemButton onClick={() => handleSelect(show)}>
                  <Box>
                    <Typography variant="body1" fontWeight="500">
                      {show.name}
                    </Typography>
                    {show.original_name && show.original_name !== show.name && (
                      <Typography variant="caption" color="text.secondary" display="block">
                        {show.original_name}
                      </Typography>
                    )}
                    {show.first_air_date && (
                      <Typography variant="caption" color="text.secondary" display="block">
                        Year: {show.first_air_date}
                      </Typography>
                    )}
                  </Box>
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="secondary">
          Cancel
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default TMDBSearchModal

