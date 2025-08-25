'use client'

import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { useApiClient } from '../hooks/useApiClient.ts'
import { useConfig, useStrategyConfigs, useIndicatorDefaults, useDefaultTimeframe } from '../contexts/ConfigContext.tsx'
import { Crypto, BacktestFormData, BacktestResponse } from '../utils/types.ts'
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

// Styled components for consistent styling
const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[1],
}))

const ResultBox = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.grey[50],
  textAlign: 'center',
}))

export const BacktestRunner = ({ selectedCrypto, onSetResult, initialResult }) => {
  const { getCryptos, runBacktest, apiClient, isLoading: apiIsLoading } = useApiClient()
  const { config, isLoading: configLoading, error: configError } = useConfig()
  const strategyConfigs = useStrategyConfigs()
  const indicatorDefaults = useIndicatorDefaults()
  const defaultTimeframe = useDefaultTimeframe()
  const queryClient = useQueryClient()
  const [result, setResult] = useState<BacktestResponse | null>(initialResult);

  useEffect(() => {
    setResult(initialResult);
  }, [initialResult]);

  // Fetch data
  const { data: cryptos, isLoading: cryptosLoading } = useQuery<{ cryptos: Crypto[] }>({
    queryKey: ['cryptos'],
    queryFn: getCryptos,
    enabled: !!apiClient, // Only enable query when apiClient is initialized
  })

  // Form handling
  const { register, handleSubmit, watch, setValue, formState: { isSubmitting } } = useForm<BacktestFormData>({
    defaultValues: {
      cryptoId: selectedCrypto || 'bitcoin',
      strategyName: 'EMA_Only',
      timeframe: parseInt(defaultTimeframe) || 30,
      parameters: {}
    }
  });

  useEffect(() => {
    if (defaultTimeframe) {
      setValue('timeframe', parseInt(defaultTimeframe));
    }
  }, [defaultTimeframe, setValue]);

  useEffect(() => {
    if (selectedCrypto) {
      setValue('cryptoId', selectedCrypto);
    }
  }, [selectedCrypto, setValue]);

  const selectedStrategy = watch('strategyName')

  // Get available strategies from config
  const availableStrategies = Object.keys(strategyConfigs).map(strategyName => ({
    name: strategyName,
    display_name: strategyName.replace(/_/g, ' '),
    description: `Strategy using: ${strategyConfigs[strategyName].long_entry.join(', ')}`
  }))

  // Get selected strategy details
  const strategyDetails = availableStrategies.find(s => s.name === selectedStrategy)

  // Generate parameter fields based on indicator defaults
  const getParameterFields = () => {
    if (!selectedStrategy || !indicatorDefaults) return []
    
    // Define which parameters are relevant for each strategy
    const strategyParameterMap = {
      'EMA_Only': [
        'short_ema', 'long_ema', 'rsi_period', 'rsi_overbought', 'rsi_oversold',
        'atr_period', 'atr_multiple', 'fixed_stop_loss_percentage', 'take_profit_multiple',
        'macd_fast_period', 'macd_slow_period', 'macd_signal_period'
      ],
      'Strict': [
        'short_sma', 'long_sma', 'rsi_period', 'rsi_overbought', 'rsi_oversold',
        'macd_fast_period', 'macd_slow_period', 'macd_signal_period',
        'atr_period', 'atr_multiple', 'fixed_stop_loss_percentage', 'take_profit_multiple'
      ],
      'BB_Breakout': [
        'bb_period', 'bb_std_dev', 'rsi_period', 'rsi_overbought', 'rsi_oversold',
        'atr_period', 'atr_multiple', 'fixed_stop_loss_percentage', 'take_profit_multiple'
      ],
      'BB_RSI': [
        'bb_period', 'bb_std_dev', 'rsi_period', 'rsi_overbought', 'rsi_oversold',
        'atr_period', 'atr_multiple', 'fixed_stop_loss_percentage', 'take_profit_multiple'
      ],
      'Combined_Trigger_Verifier': [
        'short_ema', 'long_ema', 'short_sma', 'long_sma', 'bb_period', 'bb_std_dev',
        'rsi_period', 'rsi_overbought', 'rsi_oversold',
        'macd_fast_period', 'macd_slow_period', 'macd_signal_period',
        'atr_period', 'atr_multiple', 'fixed_stop_loss_percentage', 'take_profit_multiple'
      ]
    }

    const relevantParams = strategyParameterMap[selectedStrategy] || []
    
    return relevantParams.map(paramKey => {
      const defaultValue = indicatorDefaults[paramKey]
      if (defaultValue === undefined) return null

      // Create parameter description
      const description = paramKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
      
      // Determine min/max based on parameter type
      let min = 0.001, max = 1000, step = 0.001
      
      if (paramKey.includes('period')) {
        min = 1; max = 100; step = 1
      } else if (paramKey.includes('percentage')) {
        min = 0.001; max = 0.1; step = 0.001
      } else if (paramKey.includes('multiple')) {
        min = 0.5; max = 10; step = 0.1
      } else if (paramKey.includes('overbought')) {
        min = 50; max = 95; step = 1
      } else if (paramKey.includes('oversold')) {
        min = 5; max = 50; step = 1
      } else if (paramKey.includes('std_dev')) {
        min = 1; max = 3; step = 0.1
      }

      return {
        key: paramKey,
        description,
        default: defaultValue,
        min,
        max,
        step
      }
    }).filter(Boolean)
  }

  const parameterFields = getParameterFields()

  // Backtest mutation
  const backtestMutation = useMutation({
    mutationFn: (data: BacktestFormData) => {
      const requestData = {
        crypto_id: data.cryptoId,
        strategy_name: data.strategyName,
        timeframe: Number(data.timeframe),
        parameters: data.parameters
      }
      return runBacktest(requestData)
    },
    onSuccess: (data) => {
      setResult(data)
      onSetResult(data)
      toast.success('Backtest completed successfully!')
      queryClient.invalidateQueries({ queryKey: ['backtest-history'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Backtest failed')
    }
  })

  const onSubmit = (data: BacktestFormData) => {
    backtestMutation.mutate(data)
  }

  console.log("result:", result)

  if (cryptosLoading || configLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (configError || !config) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
        <Alert severity="error">Failed to load configuration: {configError}</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ my: 3 }}>
      <StyledPaper sx={{ mb: 3 }}>
        <Typography variant="h5" component="h2" gutterBottom>
          Strategy Backtesting
        </Typography>

        <form onSubmit={handleSubmit(onSubmit)}>
          <Grid container spacing={3} mb={3}>
            {/* Cryptocurrency Selection */}
            <Grid xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel id="crypto-select-label">Cryptocurrency</InputLabel>
                <Select
                  labelId="crypto-select-label"
                  label="Cryptocurrency"
                  {...register('cryptoId', { required: true })}
                  value={watch('cryptoId')}
                  onChange={(event) => setValue('cryptoId', event.target.value as string)}
                >
                  {cryptos?.cryptos.map((crypto) => (
                    <MenuItem key={crypto.id} value={crypto.id}>
                      {crypto.name} ({crypto.symbol})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Strategy Selection */}
            <Grid xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel id="strategy-select-label">Strategy</InputLabel>
                <Select
                  labelId="strategy-select-label"
                  label="Strategy"
                  {...register('strategyName', { required: true })}
                  defaultValue="EMA_Only"
                >
                  {availableStrategies.map((strategy) => (
                    <MenuItem key={strategy.name} value={strategy.name}>
                      {strategy.display_name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Timeframe */}
            <Grid xs={12} md={4}>
              <TextField
                fullWidth
                label="Timeframe (days)"
                type="number"
                inputProps={{ min: 1, max: 365 }}
                {...register('timeframe', { required: true, min: 1, max: 365 })}
              />
            </Grid>
          </Grid>

          {/* Strategy Description */}
          {strategyDetails && (
            <Alert severity="info" sx={{ mb: 3 }}>
              <Typography variant="subtitle2" component="strong">
                {strategyDetails.display_name}:
              </Typography>{' '}
              {strategyDetails.description}
            </Alert>
          )}

          {/* Strategy Parameters */}
          {parameterFields.length > 0 && (
            <StyledPaper sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>Strategy Parameters</Typography>
              <Grid container spacing={2}>
                {parameterFields.map((param) => (
                  <Grid xs={12} sm={6} key={param.key}>
                    <TextField
                      fullWidth
                      label={param.description}
                      type="number"
                      inputProps={{ 
                        min: param.min, 
                        max: param.max, 
                        step: param.step 
                      }}
                      defaultValue={param.default}
                      {...register(`parameters.${param.key}` as any, { required: true })}
                    />
                  </Grid>
                ))}
              </Grid>
            </StyledPaper>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={isSubmitting || apiIsLoading}
            sx={{ mt: 2 }}
          >
            {isSubmitting ? 'Running Backtest...' : 'Run Backtest'}
          </Button>
        </form>
      </StyledPaper>

      {/* Results */}
      {result && (
        <StyledPaper>
          <Typography variant="h5" component="h3" gutterBottom>Backtest Results</Typography>

          <Grid container spacing={2} mb={3}>
            <Grid xs={12} sm={6} md={3}>
              <ResultBox>
                <Typography variant="body2" color="text.secondary">Total Profit</Typography>
                <Typography
                  variant="h6"
                  sx={{
                    fontWeight: 'bold',
                    color: (result?.backtest?.result?.total_profit_loss ?? 0) > 0 ? 'success.main' : ((result?.backtest?.result?.total_profit_loss ?? 0) < 0 ? 'error.main' : 'text.secondary'),
                  }}
                >
                  ${(result?.backtest?.result?.total_profit_loss ?? 0).toFixed(2)}
                </Typography>
              </ResultBox>
            </Grid>

            <Grid xs={12} sm={6} md={3}>
              <ResultBox>
                <Typography variant="body2" color="text.secondary">Number of Trades</Typography>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  {result?.backtest?.result?.total_trades !== undefined && result?.backtest?.result?.total_trades !== null
                    ? String(result.backtest.result.total_trades)
                    : 'N/A'}
                </Typography>
              </ResultBox>
            </Grid>

            <Grid xs={12} sm={6} md={3}>
              <ResultBox>
                <Typography variant="body2" color="text.secondary">Win Rate</Typography>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  {(result?.backtest?.result?.win_rate ?? 0).toFixed(1)}%
                </Typography>
              </ResultBox>
            </Grid>

            
          </Grid>

          <Grid container spacing={3}>
            <Grid xs={12} md={6}>
              <Typography variant="subtitle1" gutterBottom>Performance Metrics</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Max Drawdown:</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'medium', color: 'error.main' }}>
                    {(result?.backtest?.result?.max_drawdown ?? 0).toFixed(2)}%
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Strategy:</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'medium' }}>{result?.backtest?.strategy_name?.replace('_', ' ')}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Timeframe:</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'medium' }}>{result?.backtest?.timeframe_days} days</Typography>
                </Box>
              </Box>
            </Grid>

            <Grid xs={12} md={6}>
              <Typography variant="subtitle1" gutterBottom>Parameters Used</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {Object.entries(result?.backtest?.parameters || {}).map(([key, value]) => (
                  <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">{key.replace('_', ' ')}:</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 'medium' }}>{String(value)}</Typography>
                  </Box>
                ))}
              </Box>
            </Grid>
          </Grid>

          

          <Typography variant="caption" color="text.secondary" sx={{ mt: 3, display: 'block' }}>
            Backtest completed at {new Date(result?.backtest?.timestamp).toLocaleString()}
          </Typography>
        </StyledPaper>
      )}
    </Box>
  )
}