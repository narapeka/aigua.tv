import React, { useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Box,
  Typography,
  Collapse,
} from '@mui/material'
import StatusBadge from './common/StatusBadge'
import Button from './common/Button'
import TMDBSearchModal from './TMDBSearchModal'

const PreviewTable = ({ shows, onSelectionChange, onManualMatch }) => {
  const [searchModal, setSearchModal] = useState({ isOpen: false, folderName: null })
  const [expandedRows, setExpandedRows] = useState(new Set())

  // Helper function to get relative path for episode display
  const getEpisodeDisplayPath = (episode, showOriginalFolder) => {
    if (!episode.original_path || !showOriginalFolder) {
      return episode.original_file
    }
    
    try {
      // Extract relative path from show folder
      const episodePath = episode.original_path
      const showFolder = showOriginalFolder
      
      // Remove the show folder prefix to get relative path
      if (episodePath.startsWith(showFolder)) {
        const relativePath = episodePath.substring(showFolder.length).replace(/^[\/\\]/, '')
        return relativePath || episode.original_file
      }
      
      // Fallback: try to extract just the subfolder name if available
      const pathParts = episodePath.split(/[\/\\]/)
      const showFolderParts = showFolder.split(/[\/\\]/)
      
      if (pathParts.length > showFolderParts.length) {
        // Get the parts after the show folder
        const relativeParts = pathParts.slice(showFolderParts.length)
        return relativeParts.join('/')
      }
      
      return episode.original_file
    } catch (e) {
      return episode.original_file
    }
  }

  const toggleRow = (folderName) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(folderName)) {
      newExpanded.delete(folderName)
    } else {
      newExpanded.add(folderName)
    }
    setExpandedRows(newExpanded)
  }

  const handleSelect = (folderName, selected) => {
    onSelectionChange(folderName, selected)
  }

  const handleManualSearch = (folderName) => {
    setSearchModal({ isOpen: true, folderName })
  }

  const handleMatchSelect = (tmdbId) => {
    if (searchModal.folderName) {
      onManualMatch(searchModal.folderName, tmdbId)
    }
  }

  return (
    <div>
      <TMDBSearchModal
        isOpen={searchModal.isOpen}
        onClose={() => setSearchModal({ isOpen: false, folderName: null })}
        onSelect={handleMatchSelect}
        folderName={searchModal.folderName}
      />

      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>
                <Checkbox
                  checked={shows.every((s) => s.selected)}
                  onChange={(e) => {
                    shows.forEach((show) => handleSelect(show.folder_name, e.target.checked))
                  }}
                />
              </TableCell>
              <TableCell>Folder</TableCell>
              <TableCell>TMDB Match</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {shows.map((show) => (
              <React.Fragment key={show.folder_name}>
                <TableRow
                  hover
                  sx={{
                    cursor: show.seasons && show.seasons.length > 0 ? 'pointer' : 'default',
                  }}
                  onClick={(e) => {
                    // Don't expand if clicking on checkbox, button, or other interactive elements
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON' || e.target.closest('button') || e.target.closest('[role="checkbox"]')) {
                      return
                    }
                    if (show.seasons && show.seasons.length > 0) {
                      toggleRow(show.folder_name)
                    }
                  }}
                >
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={show.selected}
                      onChange={(e) => handleSelect(show.folder_name, e.target.checked)}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {show.folder_name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {show.tmdb_match ? (
                      <Box>
                        <Typography variant="body2" fontWeight="500">
                          {show.tmdb_match.name}
                        </Typography>
                        {show.tmdb_match.year && (
                          <Typography variant="caption" color="text.secondary">
                            ({show.tmdb_match.year})
                          </Typography>
                        )}
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No match
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <StatusBadge confidence={show.match_confidence} />
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="secondary"
                      onClick={() => handleManualSearch(show.folder_name)}
                      size="small"
                    >
                      Search
                    </Button>
                  </TableCell>
                </TableRow>
                {show.seasons && show.seasons.length > 0 && (
                  <TableRow>
                    <TableCell colSpan={5} sx={{ py: 0, border: 0 }}>
                      <Collapse in={expandedRows.has(show.folder_name)} timeout="auto" unmountOnExit>
                      <Box sx={{ p: 2, bgcolor: 'background.default' }}>
                        {show.seasons.map((season) => (
                          <Box key={season.season_number} sx={{ mb: 3 }}>
                            <Typography variant="subtitle2" gutterBottom>
                              Season {season.season_number}
                            </Typography>
                            <TableContainer>
                              <Table size="small">
                                <TableHead>
                                  <TableRow>
                                    <TableCell sx={{ width: '80px' }}>Episode</TableCell>
                                    <TableCell>Original File</TableCell>
                                    <TableCell sx={{ width: '30px' }}></TableCell>
                                    <TableCell>New File</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {season.episodes.map((ep) => {
                                    const displayPath = getEpisodeDisplayPath(ep, show.original_folder)
                                    return (
                                      <TableRow key={ep.episode_number}>
                                        <TableCell>
                                          <Typography variant="caption" fontWeight="500">
                                            S{season.season_number.toString().padStart(2, '0')}E{ep.episode_number.toString().padStart(2, '0')}
                                          </Typography>
                                        </TableCell>
                                        <TableCell>
                                          <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                                            {displayPath}
                                          </Typography>
                                        </TableCell>
                                        <TableCell sx={{ textAlign: 'center', color: 'text.secondary' }}>→</TableCell>
                                        <TableCell>
                                          <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'primary.main' }}>
                                            {ep.new_file}
                                          </Typography>
                                        </TableCell>
                                      </TableRow>
                                    )
                                  })}
                                </TableBody>
                              </Table>
                            </TableContainer>
                          </Box>
                        ))}
                      </Box>
                    </Collapse>
                  </TableCell>
                </TableRow>
                )}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  )
}

export default PreviewTable

