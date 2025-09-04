import React from 'react';
import { Alert, Button, Paper, Typography } from '@mui/material';
import { styled } from '@mui/system';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[1],
  marginBottom: theme.spacing(3),
}));

interface ErrorDisplayProps {
  error: string | null;
  onDismiss: () => void;
  onRetry?: () => void;
  is403?: boolean;
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ error, onDismiss, onRetry, is403 }) => {
  if (!error) {
    return null;
  }

  return (
    <StyledPaper>
      <Alert severity="error" action={
        <Button color="inherit" size="small" onClick={is403 && onRetry ? onRetry : onDismiss}>
          {is403 && onRetry ? 'RETRY' : 'DISMISS'}
        </Button>
      }>
        <Typography variant="h6">
          {is403 ? 'Access Forbidden' : 'An Error Occurred'}
        </Typography>
        <Typography>
          {is403 ? "You don't have permission to access this resource." : error}
        </Typography>
      </Alert>
    </StyledPaper>
  );
};