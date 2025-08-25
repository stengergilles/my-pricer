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
    setIsLoading(true) // Set loading to true when API call starts
    try {
      // Type assertion to ensure method exists on ApiClient and is callable
      const apiMethod = apiClient[method] as (...args: any[]) => Promise<any>;
      if (typeof apiMethod === 'function') {
        const response = await apiMethod(...args);
        return response;
      } else {
        throw new Error(`Method ${String(method)} is not a function on ApiClient.`);
      }
    } catch (error) {
      console.error(`API call failed for method ${String(method)}:`, error);
      throw error;
    } finally {
      setIsLoading(false) // Set loading to false when API call completes
    }
  }, [apiClient]);

  // Direct method calls that map to ApiClient methods
  const getCryptos = useCallback(async () => {
    return callApi('getCryptos');
  }, [callApi]);

  const getCrypto = useCallback(async (cryptoId: string) => {
    return callApi('getCrypto', cryptoId);
  }, [callApi]);

  const getStrategies = useCallback(async () => {
    return callApi('getStrategies');
  }, [callApi]);

  const getStrategy = useCallback(async (strategyName: string) => {
    return callApi('getStrategy', strategyName);
  }, [callApi]);

  const runAnalysis = useCallback(async (data: any) => {
    return callApi('runAnalysis', data);
  }, [callApi]);

  const getAnalysis = useCallback(async (analysisId: string) => {
    return callApi('getAnalysis', analysisId);
  }, [callApi]);

  const getAnalysisHistory = useCallback(async (cryptoId?: string, limit = 50) => {
    return callApi('getAnalysisHistory', cryptoId, limit);
  }, [callApi]);

  const runBacktest = useCallback(async (data: any) => {
    return callApi('runBacktest', data);
  }, [callApi]);

  const getBacktest = useCallback(async (backtestId: string) => {
    return callApi('getBacktest', backtestId);
  }, [callApi]);

  const getBacktestHistory = useCallback(async (cryptoId?: string, strategyName?: string, limit = 50) => {
    return callApi('getBacktestHistory', cryptoId, strategyName, limit);
  }, [callApi]);

  const healthCheck = useCallback(async () => {
    return callApi('healthCheck');
  }, [callApi]);

  const getConfig = useCallback(async () => {
    return callApi('getConfig');
  }, [callApi]);

  return { 
    apiClient, 
    getCryptos,
    getCrypto,
    getStrategies,
    getStrategy,
    runAnalysis,
    getAnalysis,
    getAnalysisHistory,
    runBacktest,
    getBacktest,
    getBacktestHistory,
    healthCheck,
    getConfig,
    isLoading, 
    setIsLoading 
  }
}