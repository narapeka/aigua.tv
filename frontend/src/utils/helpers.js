export const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString()
}

export const formatBytes = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

export const getConfidenceColor = (confidence) => {
  switch (confidence) {
    case 'high':
      return '#4caf50'
    case 'medium':
      return '#ff9800'
    case 'low':
      return '#f44336'
    default:
      return '#9e9e9e'
  }
}

