import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Paper, Typography, Grid, CircularProgress, Alert, Box, Button } from '@mui/material';
import { useApiClient } from '../hooks/useApiClient.ts';
import CurrentAnalysisTable from './results/CurrentAnalysisTable.tsx';

const PaperTradingStatus = () => {
  const { getPaperTradingStatus } = useApiClient();
  const { data, error, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['paperTradingStatus'],
    queryFn: getPaperTradingStatus,
    refetchInterval: 60000, // Refetch every 1 minute
  });

  if (isLoading && !data) { // Show loader only on initial load
    return (
      <Paper elevation={3} sx={{ p: 2, mb: 2, textAlign: 'center' }}>
        <CircularProgress />
      </Paper>
    );
  }

  if (error) {
    const errorMessage = error.message || 'Error fetching paper trading status.';
    if (errorMessage.includes('No analysis data available')) {
      return <Alert severity="warning">{errorMessage}</Alert>;
    }
    return <Alert severity="error">{errorMessage}</Alert>;
  }

  if (!data) {
    return null; // Don't render anything if there's no data yet
  }

  console.log("PaperTradingStatus data:", data); // Add this line

  const totalPnl = data.open_positions.reduce((acc, pos) => acc + (pos.pnl_usd || 0), 0);
  const totalPositionCost = data.open_positions.reduce((acc, pos) => acc + (pos.cost_usd || 0), 0);
  const availableCash = data.initial_capital - totalPositionCost;

  return (
    <Paper elevation={3} sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6">
            Paper Trading Status
          </Typography>
          <Typography variant="subtitle1" color={data.is_running ? 'success.main' : 'error.main'}>
            {data.is_running ? 'Open' : 'Closed'}
          </Typography>
        </Box>
        {dataUpdatedAt && (
          <Typography variant="caption" color="text.secondary">
            Last updated: {new Date(dataUpdatedAt).toLocaleTimeString()}
          </Typography>
        )}
      </Box>
      <Grid container spacing={2}>
        <Grid item xs={4}>
          <Typography variant="subtitle1">Portfolio Value</Typography>
          <Typography variant="h5" color={data.portfolio_value >= data.initial_capital ? 'success.main' : 'error.main'}>${data.portfolio_value.toFixed(2)}</Typography>
        </Grid>
        <Grid item xs={4}>
          <Typography variant="subtitle1">Available Cash</Typography>
          <Typography variant="h5">${availableCash.toFixed(2)}</Typography>
        </Grid>
        <Grid item xs={4}>
          <Typography variant="subtitle1">Open Positions</Typography>
          <Typography variant="h5">{data.open_positions.length}</Typography>
        </Grid>
        <Grid item xs={4}>
          <Typography variant="subtitle1">Total Open PnL</Typography>
          <Typography variant="h5" color={totalPnl >= 0 ? 'success.main' : 'error.main'}>
            ${totalPnl.toFixed(2)}
          </Typography>
        </Grid>
      </Grid>

      <Box sx={{ mt: 2 }}>
        <Typography variant="subtitle1">Monitoring</Typography>
        <Typography variant="body2" color="text.secondary">
          Last analysis run: {data.last_analysis_run ? new Date(data.last_analysis_run).toLocaleString() : 'Never'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Monitored cryptos: {data.monitored_cryptos.join(', ')}
        </Typography>
      </Box>

      {data.optimization_status && data.optimization_status.status === 'no_profitable_strategies' && (
        <Alert severity="info" sx={{ mt: 2 }}>
          {data.optimization_status.message}
          <Button color="primary" size="small" onClick={() => alert('Running optimizer...')} sx={{ ml: 2 }}>
            Run Optimizer
          </Button>
        </Alert>
      )}
      {data.optimization_status && data.optimization_status.status === 'not_found' && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          {data.optimization_status.message}
          <Button color="primary" size="small" onClick={() => alert('Running optimizer...')} sx={{ ml: 2 }}>
            Run Optimizer
          </Button>
        </Alert>
      )}
      {data.optimization_status && data.optimization_status.status === 'no_volatile_cryptos' && (
        <Alert severity="info" sx={{ mt: 2 }}>
          {data.optimization_status.message}
        </Alert>
      )}
      {data.optimization_status && data.optimization_status.status === 'some_optimized_some_not' && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          {data.optimization_status.message}
          <Button color="primary" size="small" onClick={() => alert('Running optimizer...')} sx={{ ml: 2 }}>
            Run Optimizer
          </Button>
        </Alert>
      )}
      {data.optimization_status && data.optimization_status.status === 'unknown_status' && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {data.optimization_status.message}
        </Alert>
      )}

      {data.analysis_history && data.analysis_history.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Typography variant="h6" sx={{ mr: 1 }}>Current Analysis</Typography>
            {data.last_analysis_run && (
              <Typography variant="caption" color="text.secondary">
                (Last updated: {new Date(data.last_analysis_run).toLocaleTimeString()})
              </Typography>
            )}
          </Box>
          <CurrentAnalysisTable
            currentAnalysis={data.analysis_history}
            openPositions={data.open_positions}
          />
        </Box>
      )}
    </Paper>
  );
};

export default PaperTradingStatus;