import React, { useState, useEffect, Suspense, lazy } from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { Box, CircularProgress, Typography, Container, Paper, AppBar, Toolbar, Tabs, Tab, IconButton } from '@mui/material';
import { styled } from '@mui/system';

// Import components that were in page.tsx
import { LoginButton } from './components/auth/LoginButton.tsx';
import { useAuth0 } from '@auth0/auth0-react';
import { setupRemoteLogger } from './utils/remoteLogger.ts';
import { ApiLoadingProvider } from './contexts/ApiLoadingContext.tsx';
import { ConfigProvider } from './contexts/ConfigContext.tsx';
import { APP_TITLE } from './utils/constants.ts';
import LogoutIcon from '@mui/icons-material/Logout';

const CryptoAnalysis = lazy(() => import('./components/CryptoAnalysis.tsx').then(module => ({ default: module.CryptoAnalysis })));
const BacktestRunner = lazy(() => import('./components/BacktestRunner.tsx').then(module => ({ default: module.BacktestRunner })));
const HealthStatus = lazy(() => import('./components/HealthStatus.tsx').then(module => ({ default: module.HealthStatus })));
const VolatileCryptoList = lazy(() => import('./components/VolatileCryptoList.tsx').then(module => ({ default: module.VolatileCryptoList })));
const ScheduleTab = lazy(() => import('./components/ScheduleTab.tsx').then(module => ({ default: module.ScheduleTab })));


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


function AppContent() {
  const { user, isLoading: auth0Loading, logout } = useAuth0();
  const [activeTab, setActiveTab] = useState('volatile');
  const [selectedCryptoForBacktest, setSelectedCryptoForBacktest] = useState(null);
  const [backtestResult, setBacktestResult] = useState(null);

  const { getAccessTokenSilently } = useAuth0();

  useEffect(() => {
    const timer = setTimeout(() => {
      setupRemoteLogger(getAccessTokenSilently);
    }, 1000);
    return () => clearTimeout(timer);
  }, [getAccessTokenSilently]);

  useEffect(() => {
    document.title = APP_TITLE;
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
              {APP_TITLE}
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
    <ConfigProvider>
      <Router>
        <Box sx={{ minHeight: '100vh', backgroundColor: (theme) => theme.palette.grey[50] }}>
          {/* Header */}
          <AppBar position="static" color="default" elevation={1}>
            <Toolbar>
              <Container maxWidth="xl" sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 2 }}>
                <Box>
                  <Typography variant="h5" component="h1" sx={{ fontWeight: 'bold', color: 'text.primary' }}>
                    {APP_TITLE}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Welcome back, {user.name}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
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
                <StyledTab label="Volatile Cryptos" value="volatile" />
                <StyledTab label="Analysis" value="analysis" />
                <StyledTab label="Backtest" value="backtest" />
                <StyledTab label="Schedule" value="schedule" />
              </Tabs>
            </Container>
          </Toolbar>
        </AppBar>

        {/* Main Content */}
        <Container maxWidth="xl" sx={{ py: 3 }}>
          <Box sx={{ p: 2 }}>
            <Suspense fallback={<CircularProgress />}>
              <Routes>
                <Route path="/" element={
                  activeTab === 'volatile' ? (
                    <VolatileCryptoList />
                  ) : activeTab === 'analysis' ? (
                    <CryptoAnalysis setActiveTab={setActiveTab} onRunBacktest={handleRunBacktest} />
                  ) : activeTab === 'backtest' ? (
                    <BacktestRunner
                      selectedCrypto={selectedCryptoForBacktest}
                      onSetResult={setBacktestResult}
                      initialResult={backtestResult}
                    />
                  ) : (
                    <ScheduleTab />
                  )
                } />
              </Routes>
            </Suspense>
          </Box>
        </Container>
      </Box>
    </Router>
    </ConfigProvider>
  );
}

function App() {
  return (
    <ApiLoadingProvider>
      <AppContent />
    </ApiLoadingProvider>
  );
}

export default App;
