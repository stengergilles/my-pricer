'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { useApiClient } from '../hooks/useApiClient.ts'
import { useConfig, useStrategyConfigs, useDefaultTimeframe } from '../contexts/ConfigContext.tsx'
import { Crypto, AnalysisFormData, AnalysisResult } from '../utils/types.ts'
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
  Checkbox,
  FormControlLabel,
  Alert,
} from '@mui/material'
import { styled } from '@mui/system'
import { ErrorDisplay } from './ErrorDisplay.tsx'


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

export const CryptoAnalysis = ({ setActiveTab, onRunBacktest }) => {
  console.log('CryptoAnalysis component rendering')
  const { getCryptos, runAnalysis, apiClient, isLoading: apiIsLoading } = useApiClient()
  const { config, isLoading: configLoading, error: configError } = useConfig()
  const strategyConfigs = useStrategyConfigs()
  const defaultTimeframe = useDefaultTimeframe()
  const queryClient = useQueryClient()
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Fetch data
  const { data: cryptos, isLoading: cryptosLoading } = useQuery<{ cryptos: Crypto[] }>({
    queryKey: ['cryptos'],
    queryFn: getCryptos,
    enabled: !!apiClient, // Only enable query when apiClient is initialized
  })

  console.log(`CryptoAnalysis - config:`, config);
  if (configError) {
    console.error(`CryptoAnalysis - configError:`, configError);
  }

  console.log(`CryptoAnalysis - cryptosLoading: ${cryptosLoading}, configLoading: ${configLoading}, apiIsLoading: ${apiIsLoading}`)

  // Get available strategies from config
  const availableStrategies = (strategyConfigs || []).map(strategy => ({
    name: strategy.name,
    display_name: strategy.display_name,
    description: strategy.description,
    defaults: strategy.defaults // Include defaults here
  }))

  // Form handling
  const { register, handleSubmit, watch, setValue, formState: { isSubmitting } } = useForm<AnalysisFormData>({
    defaultValues: {
      cryptoId: 'bitcoin',
      strategyName: 'EMA_Only',
      timeframe: parseInt(defaultTimeframe) || 30,
      useCustomParams: false,
      parameters: {}
    }
  });

  useEffect(() => {
    if (defaultTimeframe) {
      setValue('timeframe', parseInt(defaultTimeframe));
    }
  }, [defaultTimeframe, setValue]);

  const selectedStrategy = watch('strategyName')
  const useCustomParams = watch('useCustomParams')

  // Get selected strategy details
  const strategyDetails = availableStrategies.find(s => s.name === selectedStrategy)

  // Generate parameter fields based on strategy defaults
  const getParameterFields = () => {
    if (!selectedStrategy || !strategyDetails || !strategyDetails.defaults) return []
    
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
      const defaultValue = strategyDetails.defaults[paramKey]
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

  // Analysis mutation
  const analysisMutation = useMutation({
    mutationFn: (data: AnalysisFormData) => {
      const requestData = {
        crypto_id: data.cryptoId,
        strategy_name: data.strategyName,
        timeframe: data.timeframe,
        ...(data.useCustomParams && { parameters: data.parameters })
      }
      return runAnalysis(requestData)
    },
    onSuccess: (data) => {
      if (data.analysis && data.analysis.success === false) {
        setError(data.analysis.error || 'Analysis failed');
        setResult(null);
      } else {
        setResult(data.analysis);
      }
      queryClient.invalidateQueries({ queryKey: ['analysis-history'] })
    },
    onError: (error: any) => {
      console.error("Analysis mutation error:", error);
      setError(error.message || 'An unknown error occurred.');
    }
  })

  const onSubmit = (data: AnalysisFormData) => {
    setError(null);
    setResult(null);
    analysisMutation.mutate(data)
  }

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
      <ErrorDisplay error={error} onDismiss={() => setError(null)} />

      <StyledPaper sx={{ mb: 3 }}>
        <Typography variant="h5" component="h2" gutterBottom>
          Crypto Analysis
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
                  defaultValue="bitcoin"
                >
                  {console.log('cryptos object:', cryptos)}
                  {cryptos?.cryptos.map((crypto) => (
                    <MenuItem key={crypto.id} value={crypto.id}>
                      {crypto.name} ({crypto.symbol})
                      {crypto.has_config_params && <span style={{ color: 'green', marginLeft: '8px' }}>📋</span>}
                      {crypto.has_optimization_results && <span style={{ color: 'blue', marginLeft: '4px' }}>🎯</span>}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                📋 Has config params • 🎯 Has optimization results
              </Typography>
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

          {/* Custom Parameters Toggle */}
          <FormControlLabel
            control={
              <Checkbox
                {...register('useCustomParams')}
              />
            }
            label="Use custom parameters"
            sx={{ mb: 2 }}
          />

          {/* Custom Parameters */}
          {useCustomParams && parameterFields.length > 0 && (
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
                      {...register(`parameters.${param.key}` as any)}
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
            {isSubmitting ? 'Running Analysis...' : 'Run Analysis'}
          </Button>
        </form>
      </StyledPaper>

      {/* Results */}
      {result && (
        <StyledPaper>
          <Typography variant="h5" component="h3" gutterBottom>Analysis Results</Typography>

          <Grid container spacing={2} mb={3}>
            <Grid xs={12} sm={6} md={3}>
              <ResultBox>
                <Typography variant="body2" color="text.secondary">Current Signal</Typography>
                <Typography
                  variant="h6"
                  sx={{
                    fontWeight: 'bold',
                    color: result.current_signal === 'LONG' ? 'success.main' : result.current_signal === 'SHORT' ? 'error.main' : 'text.primary',
                  }}
                >
                  {result.current_signal}
                </Typography>
              </ResultBox>
            </Grid>

            <Grid xs={12} sm={6} md={3}>
              <ResultBox>
                <Typography variant="body2" color="text.secondary">Current Price</Typography>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  ${result.current_price.toLocaleString()}
                </Typography>
              </ResultBox>
            </Grid>

            <Grid xs={12} sm={6} md={3}>
              <ResultBox>
                <Typography variant="body2" color="text.secondary">Strategy Used</Typography>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  {result.strategy_used.replace('_', ' ')}
                </Typography>
              </ResultBox>
            </Grid>

            <Grid xs={12} sm={6} md={3}>
              <ResultBox>
                <Typography variant="body2" color="text.secondary">Timeframe</Typography>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  {result.timeframe_days} days
                </Typography>
              </ResultBox>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid xs={12} md={6}>
              <Typography variant="subtitle1" gutterBottom>Support/Resistance Analysis</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Active Resistance Lines:</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'medium' }}>{result.active_resistance_lines?.length || 0}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Active Support Lines:</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'medium' }}>{result.active_support_lines?.length || 0}</Typography>
                </Box>
              </Box>
            </Grid>

            {result.backtest_result && result.backtest_result.total_profit_percentage !== undefined ? (
              <Grid xs={12} md={6}>
                <Typography variant="subtitle1" gutterBottom>Backtest Performance</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Total Profit:</Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 'medium',
                        color: result.backtest_result.total_profit_loss > 0 ? 'success.main' : (result.backtest_result.total_profit_loss < 0 ? 'error.main' : 'text.secondary'),
                      }}
                    >
                      ${(result.backtest_result?.total_profit_loss ?? 0).toFixed(2)}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Number of Trades:</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 'medium' }}>{result.backtest_result?.total_trades ?? 0}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Win Rate:</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 'medium' }}>{(result.backtest_result?.win_rate ?? 0).toFixed(1)}%</Typography>
                  </Box>
                </Box>
              </Grid>
            ) : (
              <Grid xs={12} md={6}>
                <Typography variant="subtitle1" gutterBottom>Backtest Performance</Typography>
                <Alert severity="info">
                  <Typography variant="body2">
                    No backtest results available for this analysis.
                  </Typography>
                  <Button
                    variant="contained"
                    color="primary"
                    size="small"
                    sx={{ mt: 1 }}
                    onClick={() => onRunBacktest(watch('cryptoId'))}
                  >
                    Run New Backtest
                  </Button>
                </Alert>
              </Grid>
            )}
          </Grid>

          <Typography variant="caption" color="text.secondary" sx={{ mt: 3, display: 'block' }}>
            Analysis completed at {new Date(result.analysis_timestamp).toLocaleString()}
          </Typography>
        </StyledPaper>
      )}
    </Box>
  )
}