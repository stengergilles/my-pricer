'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../utils/api.ts'
import { HealthCheck } from '../utils/types.ts'

export function HealthStatus() {
  const { data: health, isLoading } = useQuery<HealthCheck>({
    queryKey: ['health'],
    queryFn: () => apiClient.healthCheck(),
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  if (isLoading) {
    return (
      <div className="flex items-center space-x-2">
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
        <span className="text-sm text-gray-500">Checking...</span>
      </div>
    )
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-400'
      case 'warning':
        return 'bg-yellow-400'
      case 'error':
        return 'bg-red-400'
      default:
        return 'bg-gray-400'
    }
  }

  return (
    <div className="flex items-center space-x-2">
      <div className={`w-2 h-2 rounded-full ${getStatusColor(health?.status || 'unknown')}`}></div>
      <span className="text-sm text-gray-600 capitalize">
        {health?.status || 'Unknown'}
      </span>
    </div>
  )
}
