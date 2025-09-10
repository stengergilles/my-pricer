'use client'

import { useQuery } from '@tanstack/react-query'
import { useApiClient } from '../hooks/useApiClient.ts'
import { HealthCheck } from '../utils/types.ts'
import { Box, Typography, CircularProgress } from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import { useAuth0 } from '@auth0/auth0-react'

export const HealthStatus = () => {
  const { healthCheck } = useApiClient()
  const { isAuthenticated, isLoading: authLoading } = useAuth0()
  
  const { data: health, isLoading, error } = useQuery<HealthCheck>({
    queryKey: ['health'],
    queryFn: healthCheck,
    refetchInterval: 30000,
    enabled: isAuthenticated && !authLoading, // Only run when authenticated
  })

  if (authLoading || isLoading) {
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
        return 'success.main'
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