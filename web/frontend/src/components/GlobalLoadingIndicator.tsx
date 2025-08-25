import { CircularProgress, Box } from '@mui/material'
import { useApiClient } from '../hooks/useApiClient'

export const GlobalLoadingIndicator = () => {
  const { isLoading } = useApiClient()

  if (!isLoading) return null

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(255, 255, 255, 0.7)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 9999,
      }}
    >
      <CircularProgress />
    </Box>
  )
}