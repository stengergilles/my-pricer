'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, Controller } from 'react-hook-form'
import { useApiClient } from '../hooks/useApiClient.ts'
import { useErrorHandler } from '../hooks/useErrorHandler.ts'
import { useConfig } from '../contexts/ConfigContext.tsx'
import { BacktestFormData, BacktestResponse } from '../utils/types.ts'
import { useCryptoStatus } from '../hooks/useCryptoStatus.ts'
import { Chip } from '@mui/material'
import CheckCircle from '@mui/icons-material/CheckCircle'
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
  Alert,
} from '@mui/material'
import { styled } from '@mui/system'
import { ErrorDisplay } from './ErrorDisplay.tsx'
import { BacktestResultDisplay } from './results/BacktestResultDisplay.tsx'

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  borderRadius: theme.shape.borderRadius,
  boxShadow: (theme.shadows as any)[1],
  marginTop: theme.spacing(3),
}))



export const BacktestRunner = () => {
  const { getCryptos, getStrategies, runBacktest, apiClient } = useApiClient()
  const { is403Error, handleError, reset403Error } = useErrorHandler()
  const queryClient = useQueryClient()
  const [result, setResult] = useState<BacktestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: cryptos, isLoading: cryptosLoading, error: cryptosError } = useQuery(
    {
      queryKey: ['volatileCryptos'],
      queryFn: () => getCryptos({ volatile: true }),
      enabled: !!apiClient,
    }
  )

  const { data: strategies, isLoading: strategiesLoading, error: strategiesError } = useQuery(
    {
      queryKey: ['strategies'],
      queryFn: () => getStrategies(),
      enabled: !!apiClient,
    }
  )

  const { config, isLoading: configLoading } = useConfig()

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { isSubmitting },
    control,
  } = useForm<BacktestFormData>({
    defaultValues: {
      cryptoId: '',
      strategyName: '',
      timeframe: 1,
      parameters: {},
    },
  })

  const watchedCryptoId = watch('cryptoId');
  const { data: cryptoStatus } = useCryptoStatus(watchedCryptoId);

  useEffect(() => {
    if (cryptos?.cryptos?.length > 0) {
      setValue('cryptoId', cryptos.cryptos[0].id);
    }
  }, [cryptos, setValue]);

  useEffect(() => {
    if (strategies?.strategies?.length > 0) {
      setValue('strategyName', strategies.strategies[0].name);
    }
  }, [strategies, setValue]);

  useEffect(() => {
    if (config?.default_timeframe) {
      setValue('timeframe', parseInt(config.default_timeframe, 10))
    }
  }, [config, setValue])

  const selectedStrategy = watch('strategyName')

  const strategyDetails = strategies?.strategies?.find((s: any) => s.name === selectedStrategy)

  useEffect(() => {
    if (strategyDetails) {
      // Reset parameters to defaults when strategy changes
      setValue('parameters', strategyDetails.defaults);
    }
  }, [selectedStrategy, strategyDetails, setValue]);

  const backtestMutation = useMutation({
    mutationFn: (data: BacktestFormData) => {
      const requestData = {
        action: 'backtest',
        crypto_id: data.cryptoId,
        strategy_name: data.strategyName,
        timeframe: data.timeframe,
        parameters: data.parameters,
      }
      return runBacktest(requestData)
    },
    onSuccess: (data) => {
      // console.log("BacktestRunner onSuccess data:", data); // Removed for production
      if (data.result && data.result.success === false) {
        setError(data.result.error || 'Backtest failed')
        setResult(null)
      } else {
        setResult(data.result)
      }
      queryClient.invalidateQueries({ queryKey: ['backtest-history'] })
    },
    onError: (error: any) => {
      // console.error('Backtest mutation error:', error) // Removed for production
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

  useEffect(() => {
    if (strategiesError && !handleError(strategiesError)) {
      setError(strategiesError.message)
    }
  }, [strategiesError, handleError])

  const handleRetry = () => {
    reset403Error()
    setError(null)
    queryClient.invalidateQueries({ queryKey: ['volatileCryptos'] })
    queryClient.invalidateQueries({ queryKey: ['strategies'] })
  }

  const onSubmit = (data: BacktestFormData) => {
    setError(null)
    setResult(null)

    // Convert parameter values to numbers
    const parameters: { [key: string]: number } = {}
    for (const key in data.parameters) {
      parameters[key] = Number(data.parameters[key])
    }

    backtestMutation.mutate({ ...data, parameters })
  }

  

  if (cryptosLoading || strategiesLoading || configLoading) {
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
          Strategy Backtesting
        </Typography>

        {cryptos?.cryptos && strategies?.strategies && (
          <form onSubmit={handleSubmit(onSubmit)}>
            <Grid container spacing={3} mb={3}>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel id="crypto-select-label">Cryptocurrency</InputLabel>
                  <Controller
                    name="cryptoId"
                    control={control}
                    render={({ field }) => (
                      <Select
                        {...field}
                        labelId="crypto-select-label"
                        label="Cryptocurrency"
                      >
                        {cryptos.cryptos.map((crypto: any) => (
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
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel id="strategy-select-label">Strategy</InputLabel>
                  <Controller
                    name="strategyName"
                    control={control}
                    render={({ field }) => (
                      <Select
                        {...field}
                        labelId="strategy-select-label"
                        label="Strategy"
                      >
                        {strategies.strategies.map((strategy: any) => (
                          <MenuItem key={strategy.name} value={strategy.name}>
                            {strategy.display_name}
                          </MenuItem>
                        ))}
                      </Select>
                    )}
                  />
                </FormControl>
              </Grid>
              <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Timeframe (days)"
                type="number"
                {...register('timeframe', { required: true, valueAsNumber: true })}
              />
            </Grid>
          </Grid>

          {strategyDetails && (
            <Box sx={{ mb: 3 }}>
              <Alert severity="info">
                <Typography variant="subtitle2" component="strong">
                  {strategyDetails.display_name}:
                </Typography>{' '}
                {strategyDetails.description}
              </Alert>
            </Box>
          )}

          {strategyDetails && strategyDetails.parameters && (
            <StyledPaper sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Strategy Parameters
              </Typography>
              <Grid container spacing={2}>
                {Object.keys(strategyDetails.parameters).map((paramKey) => (
                  <Grid item xs={12} sm={6} key={paramKey}>
                    <TextField
                      fullWidth
                      label={paramKey.replace(/_/g, ' ')}
                      type="number"
                      defaultValue={strategyDetails.defaults[paramKey]}
                      {...register(`parameters.${paramKey}` as any)}
                      sx={{ mt: 2 }}
                    />
                  </Grid>
                ))}
              </Grid>
            </StyledPaper>
          )}

          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={isSubmitting || backtestMutation.isPending}
            sx={{ mt: 2 }}
          >
            {isSubmitting || backtestMutation.isPending
              ? 'Running Backtest...'
              : 'Run Backtest'}
          </Button>
        </form>
        )}
      </StyledPaper>

      {(isSubmitting || backtestMutation.isPending) && (
        <StyledPaper>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: '200px',
            }}
          >
            <CircularProgress />
            <Typography sx={{ ml: 2 }}>Running backtest...</Typography>
          </Box>
        </StyledPaper>
      )}

      {result && (
        <StyledPaper>
          <Typography variant="h5" component="h3" gutterBottom>
            Backtest Results
          </Typography>
          <BacktestResultDisplay result={result} />
        </StyledPaper>
      )}
    </Box>
  )
}
