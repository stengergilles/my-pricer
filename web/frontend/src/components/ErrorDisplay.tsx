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
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ error, onDismiss }) => {
  if (!error) {
    return null;
  }

  return (
    <StyledPaper>
      <Alert severity="error" action={
        <Button color="inherit" size="small" onClick={onDismiss}>
          DISMISS
        </Button>
      }>
        <Typography variant="h6">An Error Occurred</Typography>
        <Typography>{error}</Typography>
      </Alert>
    </StyledPaper>
  );
};