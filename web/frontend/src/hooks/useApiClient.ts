import { useCallback, useMemo } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { ApiClient } from '../utils/api.ts'
import { useApiLoading } from '../contexts/ApiLoadingContext.tsx'

export const useApiClient = () => {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0()
  
  const { isLoading, startOperation, endOperation } = useApiLoading()

  const apiClient = useMemo(() => {
    if (isAuthenticated) {
      return new ApiClient(getAccessTokenSilently);
    } else {
      // If not authenticated, use a client without auth (for public endpoints)
      return new ApiClient(undefined);
    }
  }, [getAccessTokenSilently, isAuthenticated]);

  

  const callApi = useCallback(async (method: keyof ApiClient, ...args: any[]) => {
    if (!apiClient) {
      throw new Error('API client not initialized.')
    }
    
    const operationId = `${String(method)}-${Date.now()}`
    startOperation(operationId)
    
    try {
      const apiMethod = apiClient[method] as (...args: any[]) => Promise<any>;
      if (typeof apiMethod === 'function') {
        const response = await apiMethod(...args);
        return response;
      } else {
        throw new Error(`Method ${String(method)} is not a function on ApiClient.`);
      }
    } catch (error) {
      throw error;
    } finally {
      endOperation(operationId)
    }
  }, [apiClient, startOperation, endOperation]);

  // Direct method calls that map to ApiClient methods
  const getCryptos = useCallback(async (params?: { volatile?: boolean; min_volatility?: number; limit?: number; force_refresh?: boolean }) => {
    return callApi('getCryptos', params);
  }, [callApi]);

  const getCrypto = useCallback(async (cryptoId: string) => {
    return callApi('getCrypto', cryptoId);
  }, [callApi]);

  const getCryptoStatus = useCallback(async (cryptoId: string) => {
    return callApi('getCryptoStatus', cryptoId);
  }, [callApi]);

  const getStrategies = useCallback(async () => {
    return callApi('getStrategies');
  }, [callApi]);

  const getStrategy = useCallback(async (strategyName: string) => {
    return callApi('getStrategy', strategyName);
  }, [callApi]);

  const runAnalysis = useCallback(async (data: any) => {
    console.log('runAnalysis called with:', data);
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

  const getJobs = useCallback(async () => {
    return callApi('getJobs');
  }, [callApi]);

  const scheduleJob = useCallback(async (data: any) => {
    return callApi('scheduleJob', data);
  }, [callApi]);

  const deleteJob = useCallback(async (jobId: string) => {
    return callApi('deleteJob', jobId);
  }, [callApi]);

  const getJobLogs = useCallback(async (jobId: string) => {
    return callApi('getJobLogs', jobId);
  }, [callApi]);

  const getPaperTradingStatus = useCallback(async () => {
    return callApi('getPaperTradingStatus');
  }, [callApi]);

  return { 
    apiClient, 
    getCryptos,
    getCrypto,
    getCryptoStatus,
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
    getJobs,
    scheduleJob,
    deleteJob,
    getJobLogs,
    getPaperTradingStatus,
    isLoading
  }
}
