'use client'

import { useQuery } from '@tanstack/react-query'
import { useApiClient } from '../hooks/useApiClient.ts'
import { HealthCheck } from '../utils/types.ts'
import { Box, Typography, CircularProgress } from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';

export const HealthStatus = () => {
  const { apiClient } = useApiClient()
  const { data: health, isLoading } = useQuery<HealthCheck>({
    queryKey: ['health'],
    queryFn: () => apiClient.healthCheck(),
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
        return 'error.main'
      default:
        return 'text.secondary'
    }
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <FiberManualRecordIcon sx={{ fontSize: 12, color: getStatusColor(health?.status || 'unknown') }} />
      <Typography variant="caption" sx={{ textTransform: 'capitalize', color: 'text.primary' }}>
        {health?.status || 'Unknown'}
      </Typography>
    </Box>
  )
}