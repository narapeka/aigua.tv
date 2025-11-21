import React from 'react'
import { Button as MuiButton } from '@mui/material'

const Button = ({ children, onClick, disabled, variant = 'primary', ...props }) => {
  // Map our custom variants to MUI variants
  const muiVariant = variant === 'primary' ? 'contained' : 
                     variant === 'success' ? 'contained' : 
                     variant === 'danger' ? 'contained' : 
                     'outlined'
  
  const color = variant === 'success' ? 'success' : 
                variant === 'danger' ? 'error' : 
                variant === 'secondary' ? 'secondary' : 
                'primary'

  return (
    <MuiButton
      variant={muiVariant}
      color={color}
      onClick={onClick}
      disabled={disabled}
      {...props}
    >
      {children}
    </MuiButton>
  )
}

export default Button

