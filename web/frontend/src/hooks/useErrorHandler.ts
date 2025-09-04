import { useState } from 'react';

export const useErrorHandler = () => {
  const [is403Error, setIs403Error] = useState(false);

  const handleError = (error: any) => {
    if (error?.response?.status === 403) {
      setIs403Error(true);
      return true; // Indicates 403 was handled
    }
    return false; // Let other error handling proceed
  };

  const reset403Error = () => {
    setIs403Error(false);
  };

  return {
    is403Error,
    handleError,
    reset403Error
  };
};
