'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { useApiClient } from '../hooks/useApiClient.ts'
import { Crypto, Strategy, AnalysisFormData, AnalysisResult } from '../utils/types.ts'
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
  const apiClient = useApiClient()
  const queryClient = useQueryClient()
  const [result, setResult] = useState<AnalysisResult | null>(null)

  // Fetch data
  const { data: cryptos, isLoading: cryptosLoading } = useQuery<{ cryptos: Crypto[] }>({
    queryKey: ['cryptos'],
    queryFn: () => apiClient.getCryptos(),
  })

  const { data: strategies, isLoading: strategiesLoading } = useQuery<{ strategies: Strategy[] }>({
    queryKey: ['strategies'],
    queryFn: () => apiClient.getStrategies(),
  })

  // Form handling
  const { register, handleSubmit, watch, formState: { isSubmitting } } = useForm<AnalysisFormData>({
    defaultValues: {
      cryptoId: 'bitcoin',
      strategyName: 'EMA_Only',
      timeframe: 7,
      useCustomParams: false,
      parameters: {}
    }
  })

  const selectedStrategy = watch('strategyName')
  const useCustomParams = watch('useCustomParams')

  // Get selected strategy details
  const strategyDetails = strategies?.strategies.find(s => s.name === selectedStrategy)

  // Analysis mutation
  const analysisMutation = useMutation({
    mutationFn: (data: AnalysisFormData) => {
      const requestData = {
        crypto_id: data.cryptoId,
        strategy_name: data.strategyName,
        timeframe: data.timeframe,
        ...(data.useCustomParams && { parameters: data.parameters })
      }
      return apiClient.runAnalysis(requestData)
    },
    onSuccess: (data) => {
      setResult(data.analysis)
      toast.success('Analysis completed successfully!')
      queryClient.invalidateQueries({ queryKey: ['analysis-history'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Analysis failed')
    }
  })

  const onSubmit = (data: AnalysisFormData) => {
    analysisMutation.mutate(data)
  }

  if (cryptosLoading || strategiesLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ my: 3 }}>
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
                  {strategies?.strategies.map((strategy) => (
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
          {useCustomParams && strategyDetails && (
            <StyledPaper sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>Strategy Parameters</Typography>
              <Grid container spacing={2}>
                {Object.entries(strategyDetails.parameters).map(([key, param]) => (
                  <Grid xs={12} sm={6} key={key}>
                    <TextField
                      fullWidth
                      label={param.description}
                      type="number"
                      inputProps={{ min: param.min, max: param.max }}
                      defaultValue={param.default}
                      {...register(`parameters.${key}` as any)}
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
            disabled={isSubmitting}
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
                        color: result.backtest_result.total_profit_percentage > 0 ? 'success.main' : 'error.main',
                      }}
                    >
                      {(result.backtest_result?.total_profit_percentage ?? 0).toFixed(2)}%
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Number of Trades:</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 'medium' }}>{result.backtest_result?.num_trades ?? 0}</Typography>
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