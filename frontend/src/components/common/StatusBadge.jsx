import React from 'react'
import { Chip } from '@mui/material'

const StatusBadge = ({ status, confidence }) => {
  const value = status || confidence || 'unknown'
  
  // Map confidence to MUI color
  const getColor = () => {
    if (confidence === 'high') return 'success'
    if (confidence === 'medium') return 'warning'
    if (confidence === 'low') return 'error'
    return 'default'
  }

  return (
    <Chip
      label={value}
      color={getColor()}
      size="small"
      sx={{ textTransform: 'capitalize' }}
    />
  )
}

export default StatusBadge

