'use client'

import React, { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '../hooks/useApiClient.ts';
import { Crypto } from '../utils/types.ts'; // Assuming Crypto type is defined here
import { CircularProgress, Button, Typography, Paper, TableContainer, Table, TableHead, TableRow, TableCell, TableBody } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';

export const VolatileCryptoList = () => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();
  const [volatileCryptos, setVolatileCryptos] = useState<Crypto[]>([]);
  const [fetchError, setFetchError] = useState<Error | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery<Crypto[], Error>({
    queryKey: ['volatileCryptos', { forceRefresh: false }], // Initial queryKey
    queryFn: async ({ queryKey }) => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const [_, queryParams] = queryKey; // queryParams will be { forceRefresh: true }
      const response = await apiClient.getCryptos({ volatile: true, force_refresh: queryParams?.forceRefresh });
      return response.cryptos; // Assuming the API returns { cryptos: [...] }
    },
  });

  const handleRefreshClick = async () => {
    await queryClient.fetchQuery({
      queryKey: ['volatileCryptos', { forceRefresh: true }],
      queryFn: async ({ queryKey }) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const [_, queryParams] = queryKey;
        const response = await apiClient.getCryptos({ volatile: true, force_refresh: queryParams?.forceRefresh });
        return response.cryptos;
      },
    });
  };

  useEffect(() => {
    if (data) {
      setVolatileCryptos(data);
    } else if (isError) {
      setFetchError(error);
    }
  }, [data, isError, error]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <CircularProgress />
        <Typography variant="h6" className="ml-4">Loading volatile cryptocurrencies...</Typography>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="text-center p-4 text-red-600">
        <Typography variant="h6">Error: {fetchError?.message || 'Failed to fetch volatile cryptocurrencies.'}</Typography>
        <Button onClick={() => refetch()} startIcon={<RefreshIcon />} className="mt-4">
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <Paper className="p-4">
      <div className="flex justify-between items-center mb-4">
        <Typography variant="h5" component="h2">
          Volatile Cryptocurrencies
        </Typography>
        <Button onClick={handleRefreshClick} startIcon={<RefreshIcon />} variant="outlined">
          Refresh List
        </Button>
      </div>
      {volatileCryptos && volatileCryptos.length > 0 ? (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Symbol</TableCell>
                <TableCell align="right">Change % (24h)</TableCell>
                <TableCell align="right">Current Price</TableCell>
                <TableCell>Name</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {volatileCryptos.map((crypto) => (
                <TableRow key={crypto.id}>
                  <TableCell>{crypto.symbol?.toUpperCase()}</TableCell>
                  <TableCell align="right" style={{ color: (crypto.price_change_percentage_24h || 0) >= 0 ? 'green' : 'red' }}>
                    {crypto.price_change_percentage_24h?.toFixed(2)}%
                  </TableCell>
                  <TableCell align="right">${crypto.current_price?.toFixed(4)}</TableCell>
                  <TableCell>{crypto.name}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Typography variant="body1" className="text-center">
          No volatile cryptocurrencies found.
        </Typography>
      )}
    </Paper>
  );
};
