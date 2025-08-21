import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Box, CircularProgress, Typography, Container, Paper } from '@mui/material';
import './App.css'; // For global styles, if any
import './index.css'; // For global styles from CRA
import './globals.css'; // From Next.js app

// Import components that were in page.tsx
import { LoginButton } from './components/auth/LoginButton.tsx';
import { LogoutButton } from './components/auth/LogoutButton.tsx';
import { CryptoAnalysis } from './components/CryptoAnalysis.tsx';
import { BacktestRunner } from './components/BacktestRunner.tsx';
import { HealthStatus } from './components/HealthStatus.tsx';

import { useAuth0 } from '@auth0/auth0-react';


function App() {
  const { user, isLoading } = useAuth0();
  const [activeTab, setActiveTab] = useState('analysis');

  if (isLoading) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <CircularProgress size={80} thickness={5} />
      </Box>
    );
  }

  if (!user) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: (theme) => theme.palette.grey[50],
        }}
      >
        <Container maxWidth="sm">
          <Paper elevation={3} sx={{ padding: 4, textAlign: 'center', borderRadius: 2 }}>
            <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold', color: 'text.primary' }}>
              Crypto Trading System
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph sx={{ marginBottom: 4 }}>
              Advanced cryptocurrency trading analysis and backtesting platform
            </Typography>
            <LoginButton />
          </Paper>
        </Container>
      </Box>
    );
  }

  return (
    <Router>
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
                <LogoutButton />
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
            <Routes>
              <Route path="/" element={activeTab === 'analysis' ? <CryptoAnalysis /> : <BacktestRunner />} />
              {/* Add more routes as needed */}
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  );
}

export default App;