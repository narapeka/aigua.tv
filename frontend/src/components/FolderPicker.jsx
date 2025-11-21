import React, { useState } from 'react'
import { Box, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Stack } from '@mui/material'
import { Folder, InsertDriveFile } from '@mui/icons-material'
import Input from './common/Input'
import Button from './common/Button'

const FolderPicker = ({ label, value, onChange, onBrowse }) => {
  const [browsing, setBrowsing] = useState(false)
  const [path, setPath] = useState('')
  const [items, setItems] = useState([])

  const handleBrowse = async () => {
    try {
      setBrowsing(true)
      const response = await onBrowse(path || value || '')
      setItems(response.data.items || [])
      setPath(response.data.path)
    } catch (err) {
      console.error('Error browsing:', err)
    } finally {
      setBrowsing(false)
    }
  }

  const handleItemClick = (item) => {
    if (item.is_directory) {
      setPath(item.path)
      handleBrowse()
    } else {
      onChange(item.path)
    }
  }

  return (
    <Box>
      <Input
        label={label}
        value={value}
        onChange={onChange}
        placeholder="Enter folder path or click Browse"
      />
      <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
        <Button onClick={handleBrowse} disabled={browsing} variant="secondary">
          {browsing ? 'Browsing...' : 'Browse'}
        </Button>
      </Stack>
      {!browsing && items.length > 0 && (
        <Box sx={{ mt: 2, border: 1, borderColor: 'divider', borderRadius: 1, maxHeight: 200, overflow: 'auto' }}>
          <List dense>
            {items.map((item, idx) => (
              <ListItem key={idx} disablePadding>
                <ListItemButton onClick={() => handleItemClick(item)}>
                  <ListItemIcon>
                    {item.is_directory ? <Folder /> : <InsertDriveFile />}
                  </ListItemIcon>
                  <ListItemText primary={item.name} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Box>
  )
}

export default FolderPicker

