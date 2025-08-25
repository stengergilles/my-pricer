import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Box, CircularProgress, Typography, Container, Paper, AppBar, Toolbar, Tabs, Tab, IconButton } from '@mui/material';
import { styled } from '@mui/system';

// Import components that were in page.tsx
import { LoginButton } from './components/auth/LoginButton.tsx';

import { CryptoAnalysis } from './components/CryptoAnalysis.tsx';
import { BacktestRunner } from './components/BacktestRunner.tsx';
import { HealthStatus } from './components/HealthStatus.tsx';
import { LoadingStateTest } from './components/LoadingStateTest.tsx';

import { useAuth0 } from '@auth0/auth0-react';
import { useApiClient } from './hooks/useApiClient.ts';
import { setupRemoteLogger } from './utils/remoteLogger.ts';

import LogoutIcon from '@mui/icons-material/Logout';


// Styled components for navigation tabs
const StyledTab = styled(Tab)(({ theme }) => ({
  textTransform: 'none',
  fontWeight: theme.typography.fontWeightMedium,
  fontSize: theme.typography.pxToRem(14),
  padding: theme.spacing(2, 1),
  minWidth: 0, // Allow tabs to shrink
  [theme.breakpoints.up('sm')]: {
    minWidth: 0,
  },
  '&.Mui-selected': {
    color: theme.palette.primary.main,
  },
  '&:hover': {
    color: theme.palette.primary.dark,
  },
}));


function App() {
  const { user, isLoading: auth0Loading, logout } = useAuth0();
  const { isLoading: apiIsLoading } = useApiClient();
  const [activeTab, setActiveTab] = useState('analysis');
  const [selectedCryptoForBacktest, setSelectedCryptoForBacktest] = useState(null);

  // Debug logging
  console.log('App component - apiIsLoading:', apiIsLoading);

  useEffect(() => {
    setupRemoteLogger();
  }, []);

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const handleRunBacktest = (cryptoId) => {
    setSelectedCryptoForBacktest(cryptoId);
    setActiveTab('backtest');
  };

  if (auth0Loading) {
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
      <Box sx={{ minHeight: '100vh', backgroundColor: (theme) => theme.palette.grey[50] }}>
        {/* Header */}
        <AppBar position="static" color="default" elevation={1}>
          <Toolbar>
            <Container maxWidth="xl" sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 2 }}>
              <Box>
                <Typography variant="h5" component="h1" sx={{ fontWeight: 'bold', color: 'text.primary' }}>
                  Crypto Trading System
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Welcome back, {user.name}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {/* Debug: Always show loading state */}
                <Typography variant="caption" color="text.secondary">
                  Debug: {apiIsLoading ? 'LOADING' : 'IDLE'}
                </Typography>
                
                {apiIsLoading && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={20} color="primary" />
                    <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold' }}>
                      Loading...
                    </Typography>
                  </Box>
                )}
                <HealthStatus />
                <IconButton
                  color="inherit"
                  onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
                  aria-label="logout"
                >
                  <LogoutIcon />
                </IconButton>
              </Box>
            </Container>
          </Toolbar>
        </AppBar>

        {/* Navigation */}
        <AppBar position="static" color="default" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Toolbar>
            <Container maxWidth="xl">
              <Tabs value={activeTab} onChange={handleTabChange} aria-label="navigation tabs">
                <StyledTab label="Analysis" value="analysis" />
                <StyledTab label="Backtest" value="backtest" />
                <StyledTab label="Loading Test" value="loading-test" />
              </Tabs>
            </Container>
          </Toolbar>
        </AppBar>

        {/* Main Content */}
        <Container maxWidth="xl" sx={{ py: 3 }}>
          <Box sx={{ p: 2 }}>
            <Routes>
              <Route path="/" element={
                activeTab === 'analysis' ? (
                  <CryptoAnalysis setActiveTab={setActiveTab} onRunBacktest={handleRunBacktest} />
                ) : activeTab === 'backtest' ? (
                  <BacktestRunner selectedCrypto={selectedCryptoForBacktest} />
                ) : activeTab === 'loading-test' ? (
                  <LoadingStateTest />
                ) : (
                  <CryptoAnalysis setActiveTab={setActiveTab} onRunBacktest={handleRunBacktest} />
                )
              } />
            </Routes>
          </Box>
        </Container>
      </Box>
    </Router>
  );
}

export default App;