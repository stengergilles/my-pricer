import React from 'react';
import { Alert, Button, Paper, Typography } from '@mui/material';

interface ForbiddenErrorProps {
  onRetry: () => void;
}

export const ForbiddenError: React.FC<ForbiddenErrorProps> = ({ onRetry }) => {
  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Alert severity="error" action={
        <Button color="inherit" size="small" onClick={onRetry}>
          RETRY
        </Button>
      }>
        <Typography variant="h6">Access Forbidden</Typography>
        <Typography>You don't have permission to access this resource.</Typography>
      </Alert>
    </Paper>
  );
};
