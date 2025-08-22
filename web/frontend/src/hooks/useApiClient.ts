import { useMemo } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { ApiClient } from '../utils/api.ts'; // Import the ApiClient class

export const useApiClient = () => {
  const { getAccessTokenSilently } = useAuth0();

  const apiClient = useMemo(() => {
    return new ApiClient(getAccessTokenSilently);
  }, [getAccessTokenSilently]);

  return apiClient;
};