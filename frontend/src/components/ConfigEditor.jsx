import React, { useState, useEffect } from 'react'
import { Container, Box, Typography, Paper, Alert, Stack, CircularProgress } from '@mui/material'
import { configApi } from '../services/api'
import Input from './common/Input'
import Button from './common/Button'

const ConfigEditor = () => {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const response = await configApi.get()
      setConfig(response.data)
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(false)
      await configApi.update(config)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setSaving(false)
    }
  }

  const updateConfig = (section, field, value) => {
    setConfig((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }))
  }

  if (loading) {
    return (
      <Container maxWidth="md">
        <Box sx={{ py: 4, textAlign: 'center' }}>
          <CircularProgress />
          <Typography variant="h6" sx={{ mt: 2 }}>Loading configuration...</Typography>
        </Box>
      </Container>
    )
  }

  if (!config) {
    return (
      <Container maxWidth="md">
        <Box sx={{ py: 4 }}>
          <Alert severity="error">Failed to load configuration</Alert>
        </Box>
      </Container>
    )
  }

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Configuration
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 3 }}>
            Configuration saved successfully!
          </Alert>
        )}

        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            LLM Settings
          </Typography>
        <Input
          label="API Key"
          type="password"
          value={config.llm.api_key}
          onChange={(value) => updateConfig('llm', 'api_key', value)}
          placeholder="Leave empty to use environment variable"
        />
        <Input
          label="Base URL"
          value={config.llm.base_url}
          onChange={(value) => updateConfig('llm', 'base_url', value)}
          placeholder="Leave empty for default"
        />
        <Input
          label="Model"
          value={config.llm.model}
          onChange={(value) => updateConfig('llm', 'model', value)}
        />
        <Input
          label="Batch Size"
          type="number"
          value={config.llm.batch_size}
          onChange={(value) => updateConfig('llm', 'batch_size', parseInt(value) || 50)}
        />
        <Input
          label="Rate Limit (req/sec)"
          type="number"
          value={config.llm.rate_limit}
          onChange={(value) => updateConfig('llm', 'rate_limit', parseInt(value) || 2)}
        />
        </Paper>

        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            TMDB Settings
          </Typography>
        <Input
          label="API Key"
          type="password"
          value={config.tmdb.api_key}
          onChange={(value) => updateConfig('tmdb', 'api_key', value)}
          placeholder="Leave empty to use environment variable"
        />
        <Input
          label="Languages (comma-separated)"
          value={config.tmdb.languages?.join(', ') || ''}
          onChange={(value) =>
            updateConfig(
              'tmdb',
              'languages',
              value.split(',').map((s) => s.trim()).filter(Boolean)
            )
          }
        />
        <Input
          label="Rate Limit (req/sec)"
          type="number"
          value={config.tmdb.rate_limit}
          onChange={(value) => updateConfig('tmdb', 'rate_limit', parseInt(value) || 40)}
        />
        </Paper>

        {config.proxy && (
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Proxy Settings
            </Typography>
          <Input
            label="Host"
            value={config.proxy.host}
            onChange={(value) => updateConfig('proxy', 'host', value)}
          />
          <Input
            label="Port"
            type="number"
            value={config.proxy.port}
            onChange={(value) => updateConfig('proxy', 'port', parseInt(value) || 8080)}
          />
          </Paper>
        )}

        <Stack direction="row" spacing={2}>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Configuration'}
          </Button>
          <Button onClick={loadConfig} variant="secondary">
            Reload
          </Button>
        </Stack>
      </Box>
    </Container>
  )
}

export default ConfigEditor

