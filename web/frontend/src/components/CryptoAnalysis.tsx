'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, Controller } from 'react-hook-form'
import { useCryptoStatus } from '../hooks/useCryptoStatus.ts'
import { Chip } from '@mui/material'
import CheckCircle from '@mui/icons-material/CheckCircle'
import { useApiClient } from '../hooks/useApiClient.ts'
import { useErrorHandler } from '../hooks/useErrorHandler.ts'
import { useConfig } from '../contexts/ConfigContext.tsx'
import { Crypto, AnalysisFormData, AnalysisResult, BacktestResponse } from '../utils/types'
import {
  Box,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Paper,
  CircularProgress,
} from '@mui/material'
import { styled } from '@mui/system'
import { ErrorDisplay } from './ErrorDisplay.tsx'
import { AnalysisResultDisplay } from './results/AnalysisResultDisplay.tsx'

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows?.[1],
  marginTop: theme.spacing(3),
}))



export const CryptoAnalysis = () => {
  const { getCryptos, runAnalysis, apiClient, getBacktestHistory } = useApiClient()
  const { is403Error, handleError, reset403Error } = useErrorHandler()
  const queryClient = useQueryClient()
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [selectedBacktest, setSelectedBacktest] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null)

  const { data: cryptos, isLoading: cryptosLoading, error: cryptosError } = useQuery<{
    cryptos: Crypto[]
  }>({
    queryKey: ['volatileCryptos'],
    queryFn: () => getCryptos({ volatile: true }),
    enabled: !!apiClient,
  })

  const { config, isLoading: configLoading } = useConfig()

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    control,
    formState: { isSubmitting },
  } = useForm<AnalysisFormData>({
    defaultValues: {
      cryptoId: '',
      timeframe: 1,
    },
  })

  const watchedCryptoId = watch('cryptoId');
  const { data: cryptoStatus } = useCryptoStatus(watchedCryptoId);

  const { data: backtestHistoryData, isLoading: backtestHistoryLoading } = useQuery({
    queryKey: ['backtestHistory', watchedCryptoId],
    queryFn: () => getBacktestHistory(watchedCryptoId),
    enabled: !!watchedCryptoId,
  });

  const backtestHistory: BacktestResponse[] = backtestHistoryData?.backtests || [];

  useEffect(() => {
    if (cryptos && cryptos.cryptos && cryptos.cryptos.length > 0) {
      setValue('cryptoId', cryptos.cryptos[0].id);
    }
  }, [cryptos, setValue]);

  useEffect(() => {
    if (config?.default_timeframe) {
      setValue('timeframe', parseInt(config.default_timeframe, 10))
    }
  }, [config, setValue])

  const analysisMutation = useMutation({
    mutationFn: (data: AnalysisFormData) => {
      const requestData = {
        crypto_id: data.cryptoId,
        timeframe: data.timeframe,
      }
      return runAnalysis(requestData)
    },
    onSuccess: (data, variables) => {
      if (data.result && data.result.success === false) {
        setError(data.result.error || 'Analysis failed')
        setResult(null)
        setSelectedBacktest(null);
      } else {
        setResult(data.result)
        setSelectedBacktest(data.result);

        // Manually update the backtest history query cache
        queryClient.setQueryData(['backtestHistory', variables.cryptoId], (oldData) => {
            const newBacktest = {
                backtest_id: data.result.analysis_id,
                crypto: data.result.crypto_id,
                strategy: data.result.strategy_used,
                parameters: data.result.parameters_used,
                timestamp: data.result.analysis_timestamp,
                engine_version: data.result.engine_version,
                result_path: data.result.result_path,
                chart_data: data.result.chart_data,
                backtest_result: data.result.backtest_result,
            };

            const existingBacktests = oldData?.backtests || [];
            // Avoid adding duplicates
            if (existingBacktests.find(b => b.backtest_id === newBacktest.backtest_id)) {
                return oldData;
            }

            return {
                backtests: [newBacktest, ...existingBacktests]
            }
        });
      }
      queryClient.invalidateQueries({ queryKey: ['analysis-history'] })
      queryClient.invalidateQueries({ queryKey: ['cryptoStatus', variables.cryptoId] })
    },
    onError: (error: any) => {
      // console.error('Analysis mutation error:', error) // Removed for production
      if (!handleError(error)) {
        setError(error.message || 'An unknown error occurred.')
      }
    },
  })

  // Handle 403 errors from queries
  useEffect(() => {
    if (cryptosError && !handleError(cryptosError)) {
      setError(cryptosError.message)
    }
  }, [cryptosError, handleError])

  const handleRetry = () => {
    reset403Error()
    setError(null)
    queryClient.invalidateQueries({ queryKey: ['volatileCryptos'] })
  }

  const onSubmit = (data: AnalysisFormData) => {
    setError(null)
    setResult(null)
    setSelectedBacktest(null);
    analysisMutation.mutate(data)
  }

  const handleBacktestSelect = (backtest: BacktestResponse) => {
    const analysisResult: AnalysisResult = {
      analysis_id: backtest.backtest_id,
      crypto_id: backtest.crypto,
      strategy_used: backtest.strategy,
      current_signal: 'HOLD', // Not available in backtest results
      current_price: 0, // Not available in backtest results
      analysis_timestamp: backtest.timestamp,
      active_resistance_lines: [], // Not available in backtest results
      active_support_lines: [], // Not available in backtest results
      parameters_used: backtest.parameters,
      timeframe_days: 0, // Not available in backtest results
      engine_version: backtest.engine_version,
      result_path: backtest.result_path,
      chart_data: backtest.chart_data,
      backtest_result: backtest.backtest_result,
    };
    setSelectedBacktest(analysisResult);
  };

  if (cryptosLoading || configLoading || backtestHistoryLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '200px',
        }}
      >
        <CircularProgress />
      </Box>
    )
  }

  if (is403Error) {
    return <ErrorDisplay error="403 Forbidden" onRetry={handleRetry} is403={true} onDismiss={() => {}} />
  }

  return (
    <Box sx={{ my: 3 }}>
      <ErrorDisplay error={error} onDismiss={() => setError(null)} />

      <StyledPaper>
        <Typography variant="h5" component="h2" gutterBottom>
          Crypto Analysis
        </Typography>

        <form onSubmit={handleSubmit(onSubmit)}>
          <Grid container spacing={3} mb={3} alignItems="center">
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel id="crypto-select-label">
                  Cryptocurrency
                </InputLabel>
                <Controller
                  name="cryptoId"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      labelId="crypto-select-label"
                      label="Cryptocurrency"
                    >
                      {cryptos?.cryptos?.map((crypto) => (
                        <MenuItem key={crypto.id} value={crypto.id}>
                          {crypto.name} ({crypto.symbol.toUpperCase()})
                        </MenuItem>
                      ))}
                    </Select>
                  )}
                />
                              {cryptoStatus?.has_optimization_results && (
                  <Chip
                    icon={<CheckCircle />}
                    label="Optimized"
                    size="small"
                    color="success"
                    variant="outlined"
                    sx={{ mt: 1 }}
                  />
                )}
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <TextField
                fullWidth
                label="Timeframe (days)"
                type="number"
                {...register('timeframe', { required: true, valueAsNumber: true })}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                disabled={isSubmitting || analysisMutation.isPending}
                fullWidth
                sx={{ height: '56px' }}
              >
                {isSubmitting || analysisMutation.isPending
                  ? 'Running...'
                  : 'Run Analysis'}
              </Button>
            </Grid>
          </Grid>
        </form>
      </StyledPaper>

      {(isSubmitting || analysisMutation.isPending) && (
        <StyledPaper>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: '200px',
            }}
          >
            <Typography sx={{ ml: 2 }}>Running analysis...</Typography>
          </Box>
        </StyledPaper>
      )}

      {result && (
        <StyledPaper>
          <Typography variant="h5" component="h3" gutterBottom>
            Analysis Results
          </Typography>
          <AnalysisResultDisplay result={selectedBacktest || result} backtestHistory={backtestHistory} onBacktestSelect={handleBacktestSelect} />
        </StyledPaper>
      )}
    </Box>
  )
}