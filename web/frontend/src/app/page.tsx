'use client'

import { useUser } from '@auth0/nextjs-auth0/client'
import { useState } from 'react'
import { LoginButton } from '@/components/auth/LoginButton'
import { useAuth0 } from '@auth0/auth0-react';
import LogoutIcon from '@mui/icons-material/Logout';
import { CryptoAnalysis } from '@/components/CryptoAnalysis'
import { BacktestRunner } from '@/components/BacktestRunner'
import { HealthStatus } from '@/components/HealthStatus'

export default function Home() {
  console.log('app/page.tsx render - backtestResult:', backtestResult);
  const { user, isLoading } = useUser()
  const [activeTab, setActiveTab] = useState('analysis')
  const [backtestResult, setBacktestResult] = useState(null);

  useEffect(() => {
    console.log('app/page.tsx - backtestResult changed:', backtestResult);
  }, [backtestResult]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8 p-8">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Crypto Trading System
            </h1>
            <p className="text-gray-600 mb-8">
              Advanced cryptocurrency trading analysis and backtesting platform
            </p>
            <LoginButton />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Crypto Trading System
              </h1>
              <p className="text-gray-600">
                Welcome back, {user.name}
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <HealthStatus />
              <button
                onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
                className="p-2 rounded-full hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                aria-label="Logout"
              >
                <LogoutIcon className="h-6 w-6 text-gray-600" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('analysis')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'analysis'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Analysis
            </button>
            <button
              onClick={() => setActiveTab('backtest')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'backtest'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Backtest
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {activeTab === 'analysis' && <CryptoAnalysis />}
          {activeTab === 'backtest' && <BacktestRunner key={backtestResult?.backtest_id || 'initial'} selectedCrypto="bitcoin" onSetResult={setBacktestResult} initialResult={backtestResult} />}
        </div>
      </main>
    </div>
  )
}
