'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { apiClient } from '@/lib/api'
import { Crypto, Strategy, BacktestFormData, BacktestResponse } from '@/lib/types'

export function BacktestRunner() {
  const queryClient = useQueryClient()
  const [result, setResult] = useState<BacktestResponse | null>(null)

  // Fetch data
  const { data: cryptos } = useQuery<{ cryptos: Crypto[] }>({
    queryKey: ['cryptos'],
    queryFn: () => apiClient.getCryptos(),
  })

  const { data: strategies } = useQuery<{ strategies: Strategy[] }>({
    queryKey: ['strategies'],
    queryFn: () => apiClient.getStrategies(),
  })

  // Form handling
  const { register, handleSubmit, watch, formState: { isSubmitting } } = useForm<BacktestFormData>({
    defaultValues: {
      cryptoId: 'bitcoin',
      strategyName: 'EMA_Only',
      timeframe: 30,
      parameters: {}
    }
  })

  const selectedStrategy = watch('strategyName')

  // Get selected strategy details
  const strategyDetails = strategies?.strategies.find(s => s.name === selectedStrategy)

  // Backtest mutation
  const backtestMutation = useMutation({
    mutationFn: (data: BacktestFormData) => {
      const requestData = {
        crypto_id: data.cryptoId,
        strategy_name: data.strategyName,
        timeframe: data.timeframe,
        parameters: data.parameters
      }
      return apiClient.runBacktest(requestData)
    },
    onSuccess: (data) => {
      setResult(data.backtest)
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

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Strategy Backtesting
        </h2>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Cryptocurrency Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cryptocurrency
              </label>
              <select
                {...register('cryptoId', { required: true })}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                {cryptos?.cryptos.map((crypto) => (
                  <option key={crypto.id} value={crypto.id}>
                    {crypto.name} ({crypto.symbol})
                  </option>
                ))}
              </select>
            </div>

            {/* Strategy Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Strategy
              </label>
              <select
                {...register('strategyName', { required: true })}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                {strategies?.strategies.map((strategy) => (
                  <option key={strategy.name} value={strategy.name}>
                    {strategy.display_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Timeframe */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Timeframe (days)
              </label>
              <input
                type="number"
                min="1"
                max="365"
                {...register('timeframe', { required: true, min: 1, max: 365 })}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Strategy Description */}
          {strategyDetails && (
            <div className="bg-blue-50 p-3 rounded-md">
              <p className="text-sm text-blue-800">
                <strong>{strategyDetails.display_name}:</strong> {strategyDetails.description}
              </p>
            </div>
          )}

          {/* Strategy Parameters */}
          {strategyDetails && (
            <div className="bg-gray-50 p-4 rounded-md space-y-3">
              <h4 className="text-sm font-medium text-gray-900">Strategy Parameters</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(strategyDetails.parameters).map(([key, param]) => (
                  <div key={key}>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      {param.description}
                    </label>
                    <input
                      type="number"
                      min={param.min}
                      max={param.max}
                      defaultValue={param.default}
                      {...register(`parameters.${key}` as any, { required: true })}
                      className="w-full p-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full md:w-auto bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Running Backtest...' : 'Run Backtest'}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Backtest Results</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 p-4 rounded-md">
              <div className="text-sm font-medium text-gray-500">Total Profit</div>
              <div className={`text-lg font-semibold ${
                result.result.total_profit_percentage > 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {result.result.total_profit_percentage.toFixed(2)}%
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-md">
              <div className="text-sm font-medium text-gray-500">Number of Trades</div>
              <div className="text-lg font-semibold text-gray-900">
                {result.result.num_trades}
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-md">
              <div className="text-sm font-medium text-gray-500">Win Rate</div>
              <div className="text-lg font-semibold text-gray-900">
                {result.result.win_rate.toFixed(1)}%
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-md">
              <div className="text-sm font-medium text-gray-500">Sharpe Ratio</div>
              <div className="text-lg font-semibold text-gray-900">
                {result.result.sharpe_ratio.toFixed(2)}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">Performance Metrics</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Max Drawdown:</span>
                  <span className="font-medium text-red-600">
                    {result.result.max_drawdown.toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Strategy:</span>
                  <span className="font-medium">{result.strategy_name.replace('_', ' ')}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Timeframe:</span>
                  <span className="font-medium">{result.timeframe_days} days</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">Parameters Used</h4>
              <div className="space-y-2">
                {Object.entries(result.parameters).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-gray-600">{key.replace('_', ' ')}:</span>
                    <span className="font-medium">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {result.result.note && (
            <div className="mt-4 p-3 bg-yellow-50 rounded-md">
              <p className="text-sm text-yellow-800">
                <strong>Note:</strong> {result.result.note}
              </p>
            </div>
          )}

          <div className="mt-4 text-xs text-gray-500">
            Backtest completed at {new Date(result.timestamp).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  )
}
