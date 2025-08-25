import { useState, useEffect, useCallback } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { ApiClient } from '../utils/api.ts'

export const useApiClient = () => {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0()
  const [apiClient, setApiClient] = useState<ApiClient | null>(null)
  const [isLoading, setIsLoading] = useState(false) // Reintroduced: Progress reporting

  useEffect(() => {
    if (isAuthenticated) {
      setApiClient(new ApiClient(getAccessTokenSilently))
    } else {
      // If not authenticated, use a client without auth (for public endpoints)
      setApiClient(new ApiClient(undefined))
    }
  }, [getAccessTokenSilently, isAuthenticated])

  const callApi = useCallback(async (method: keyof ApiClient, ...args: any[]) => {
    if (!apiClient) {
      throw new Error('API client not initialized.')
    }
    setIsLoading(true) // Reintroduced: Progress reporting
    try {
      // Type assertion to ensure method exists on ApiClient and is callable
      const apiMethod = apiClient[method] as (...args: any[]) => Promise<any>;
      if (typeof apiMethod === 'function') {
        const response = await apiMethod(...args);
        return response;
      } else {
        throw new Error(`Method ${String(method)} is not a function on ApiClient.`);
      }
    } finally {
      setIsLoading(false) // Reintroduced: Progress reporting
    }
  }, [apiClient, setIsLoading]);

  const get = useCallback(async (endpoint: string, ...args: any[]) => {
    return callApi(endpoint as any, ...args);
  }, [callApi]);

  const post = useCallback(async (endpoint: string, ...args: any[]) => {
    return callApi(endpoint as any, ...args);
  }, [callApi]);

  const put = useCallback(async (endpoint: string, ...args: any[]) => {
    return callApi(endpoint as any, ...args);
  }, [callApi]);

  const del = useCallback(async (endpoint: string, ...args: any[]) => {
    return callApi(endpoint as any, ...args);
  }, [callApi]);

  return { apiClient, get, post, put, del, isLoading, setIsLoading }
}