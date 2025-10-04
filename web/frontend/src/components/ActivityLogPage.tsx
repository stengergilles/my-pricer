import React from 'react';
import { Container, Typography, Box } from '@mui/material';
import TraderActivityLog from './TraderActivityLog.tsx';

const ActivityLogPage: React.FC = () => {
  return (
    <Container maxWidth="xl">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Trader Activity Log
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          This page displays a real-time stream of the paper trading engine's actions and decisions.
        </Typography>
        <TraderActivityLog />
      </Box>
    </Container>
  );
};

export default ActivityLogPage;
