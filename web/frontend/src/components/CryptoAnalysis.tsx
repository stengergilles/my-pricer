'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { apiClient } from '@/lib/api'
import { Crypto, Strategy, AnalysisFormData, AnalysisResult } from '@/lib/types'

export function CryptoAnalysis() {
  const queryClient = useQueryClient()
  const [result, setResult] = useState<AnalysisResult | null>(null)

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

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Crypto Analysis
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

          {/* Custom Parameters Toggle */}
          <div className="flex items-center">
            <input
              type="checkbox"
              {...register('useCustomParams')}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label className="ml-2 block text-sm text-gray-900">
              Use custom parameters
            </label>
          </div>

          {/* Custom Parameters */}
          {useCustomParams && strategyDetails && (
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
                      {...register(`parameters.${key}` as any)}
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
            {isSubmitting ? 'Running Analysis...' : 'Run Analysis'}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Analysis Results</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 p-4 rounded-md">
              <div className="text-sm font-medium text-gray-500">Current Signal</div>
              <div className={`text-lg font-semibold ${
                result.current_signal === 'LONG' ? 'text-green-600' :
                result.current_signal === 'SHORT' ? 'text-red-600' : 'text-gray-600'
              }`}>
                {result.current_signal}
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-md">
              <div className="text-sm font-medium text-gray-500">Current Price</div>
              <div className="text-lg font-semibold text-gray-900">
                ${result.current_price.toLocaleString()}
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-md">
              <div className="text-sm font-medium text-gray-500">Strategy Used</div>
              <div className="text-lg font-semibold text-gray-900">
                {result.strategy_used.replace('_', ' ')}
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-md">
              <div className="text-sm font-medium text-gray-500">Timeframe</div>
              <div className="text-lg font-semibold text-gray-900">
                {result.timeframe_days} days
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">Support/Resistance Analysis</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Active Resistance Lines:</span>
                  <span className="font-medium">{result.active_resistance_lines?.length || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Active Support Lines:</span>
                  <span className="font-medium">{result.active_support_lines?.length || 0}</span>
                </div>
              </div>
            </div>

            {result.backtest_result && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">Backtest Performance</h4>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Total Profit:</span>
                    <span className={`font-medium ${
                      result.backtest_result.total_profit_percentage > 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {result.backtest_result.total_profit_percentage.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Number of Trades:</span>
                    <span className="font-medium">{result.backtest_result.num_trades}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Win Rate:</span>
                    <span className="font-medium">{result.backtest_result.win_rate.toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="mt-4 text-xs text-gray-500">
            Analysis completed at {new Date(result.analysis_timestamp).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  )
}
