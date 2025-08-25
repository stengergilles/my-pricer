import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { ApiClient } from '../utils/api.ts'

interface StrategyConfig {
  long_entry: string[]
  short_entry: string[]
  long_exit: string[]
  short_exit: string[]
}

interface IndicatorDefaults {
  [key: string]: number | string
}

interface BacktestConfig {
  duration: string
  freq: string
}

interface ParamSet {
  [key: string]: [number, number, number] // [min, max, step]
}

interface ConfigData {
  strategy_configs: { [key: string]: StrategyConfig }
  atr_period: number
  atr_multiple: number
  default_timeframe: string
  default_interval: string
  default_spread_percentage: number
  default_slippage_percentage: number
  indicator_defaults: IndicatorDefaults
  backtest_configs: { [key: string]: BacktestConfig }
  param_sets: { [key: string]: { [key: string]: ParamSet } }
}

interface ConfigContextType {
  config: ConfigData | null
  isLoading: boolean
  error: string | null
  refetch: () => Promise<void>
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined)

interface ConfigProviderProps {
  children: ReactNode
}

export const ConfigProvider: React.FC<ConfigProviderProps> = ({ children }) => {
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchConfig = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      // Create a direct API client instance for config fetching
      const apiClient = new ApiClient(undefined) // No auth needed for config
      const response = await apiClient.getConfig()
      setConfig(response)
    } catch (err) {
      console.error('Failed to fetch config:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch configuration')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchConfig()
  }, [])

  const refetch = async () => {
    await fetchConfig()
  }

  return (
    <ConfigContext.Provider value={{ config, isLoading, error, refetch }}>
      {children}
    </ConfigContext.Provider>
  )
}

export const useConfig = (): ConfigContextType => {
  const context = useContext(ConfigContext)
  if (context === undefined) {
    throw new Error('useConfig must be used within a ConfigProvider')
  }
  return context
}

// Helper hooks for specific config sections
export const useStrategyConfigs = () => {
  const { config } = useConfig()
  return config?.strategies || []
}

export const useIndicatorDefaults = () => {
  const { config } = useConfig()
  return config?.indicator_defaults || {}
}

export const useDefaultTimeframe = () => {
  const { config } = useConfig()
  return config?.default_timeframe || '30'
}

export const useDefaultSpread = () => {
  const { config } = useConfig()
  return config?.default_spread_percentage || 0.01
}

export const useParamSets = () => {
  const { config } = useConfig()
  return config?.param_sets || {}
}
