import { useState, useEffect } from 'react'
import { Box, Typography, Card, CardContent, TextField, Button, Alert } from '@mui/material'
import { Save } from '@mui/icons-material'
import { configApi } from '../services/api'
import type { ConfigData } from '../types'

export default function ConfigPage() {
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const data = await configApi.getConfig()
      setConfig(data)
    } catch (error: any) {
      setError('Failed to load configuration')
    }
  }

  const handleSave = async () => {
    if (!config) return

    setIsLoading(true)
    setError(null)
    setSuccess(false)

    try {
      await configApi.updateConfig(config)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (error: any) {
      setError('Failed to save configuration')
    } finally {
      setIsLoading(false)
    }
  }

  if (!config) {
    return <Typography>Loading...</Typography>
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>
        Configuration
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Configuration saved successfully
        </Alert>
      )}

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            LLM Configuration
          </Typography>
          <TextField
            fullWidth
            label="API Key"
            type="password"
            value={config.llm.api_key || ''}
            onChange={(e) =>
              setConfig({ ...config, llm: { ...config.llm, api_key: e.target.value } })
            }
            margin="normal"
          />
          <TextField
            fullWidth
            label="Model"
            value={config.llm.model || ''}
            onChange={(e) =>
              setConfig({ ...config, llm: { ...config.llm, model: e.target.value } })
            }
            margin="normal"
          />
        </CardContent>
      </Card>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            TMDB Configuration
          </Typography>
          <TextField
            fullWidth
            label="API Key"
            type="password"
            value={config.tmdb.api_key || ''}
            onChange={(e) =>
              setConfig({ ...config, tmdb: { ...config.tmdb, api_key: e.target.value } })
            }
            margin="normal"
          />
        </CardContent>
      </Card>

      <Button
        fullWidth
        variant="contained"
        size="large"
        startIcon={<Save />}
        onClick={handleSave}
        disabled={isLoading}
      >
        {isLoading ? 'Saving...' : 'Save Configuration'}
      </Button>
    </Box>
  )
}
