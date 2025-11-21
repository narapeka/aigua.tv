import React from 'react'
import { TextField } from '@mui/material'

const Input = ({ label, value, onChange, type = 'text', placeholder, onKeyPress, ...props }) => {
  return (
    <TextField
      label={label}
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onKeyPress={onKeyPress}
      placeholder={placeholder}
      fullWidth
      variant="outlined"
      margin="normal"
      {...props}
    />
  )
}

export default Input

