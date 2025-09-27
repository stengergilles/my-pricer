import { useState } from 'react';

export const useErrorHandler = () => {
  const [is403Error, setIs403Error] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleError = (error: any) => {
    if (error?.response?.status === 403) {
      setIs403Error(true);
      return true; // Indicates 403 was handled
    }
    setErrorMessage(error.message || 'An unexpected error occurred.'); // Set generic error message
    return false; // Let other error handling proceed
  };

  const showError = (message: string) => {
    setErrorMessage(message);
  };

  const clearError = () => {
    setErrorMessage(null);
  };

  const reset403Error = () => {
    setIs403Error(false);
  };

  return {
    is403Error,
    errorMessage,
    handleError,
    showError,
    clearError,
    reset403Error
  };
};
