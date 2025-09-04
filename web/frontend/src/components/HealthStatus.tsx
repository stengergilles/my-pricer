'use client'

import { useQuery } from '@tanstack/react-query'
import { useApiClient } from '../hooks/useApiClient.ts'
import { HealthCheck } from '../utils/types.ts'
import { Box, Typography, CircularProgress } from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';

export const HealthStatus = () => {
  const { healthCheck } = useApiClient()
  const { data: health, isLoading, error } = useQuery<HealthCheck>({
    queryKey: ['health'],
    queryFn: healthCheck,
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CircularProgress size={12} color="inherit" />
        <Typography variant="caption" color="text.secondary">Checking...</Typography>
      </Box>
    )
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success.main' // MUI color palette
      case 'warning':
        return 'warning.main'
      case 'error':
      case 'forbidden':
        return 'error.main'
      default:
        return 'text.secondary'
    }
  }

  const getStatusText = () => {
    if (error?.response?.status === 403) {
      return 'Forbidden'
    }
    return health?.status || 'Unknown'
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <FiberManualRecordIcon sx={{ fontSize: 12, color: getStatusColor(getStatusText().toLowerCase()) }} />
      <Typography variant="caption" sx={{ textTransform: 'capitalize', color: 'text.primary' }}>
        {getStatusText()}
      </Typography>
    </Box>
  )
}