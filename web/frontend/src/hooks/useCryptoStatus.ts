import { useQuery } from '@tanstack/react-query';
import { useApiClient } from './useApiClient.ts'; // Added .ts extension

interface CryptoStatus {
  crypto_id: string;
  has_config_params: boolean;
  has_optimization_results: boolean;
}

export const useCryptoStatus = (cryptoId: string) => {
  const { getCryptoStatus, apiClient } = useApiClient();

  return useQuery<CryptoStatus>({
    queryKey: ['cryptoStatus', cryptoId],
    queryFn: () => getCryptoStatus(cryptoId),
    enabled: !!apiClient && !!cryptoId, // Only enable query when apiClient is initialized and cryptoId is available
    staleTime: Infinity, // Cache status indefinitely
  });
};
