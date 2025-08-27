import React from 'react';
import { MenuItem } from '@mui/material';
// import { useCryptoStatus } from '../hooks/useCryptoStatus.ts'; // Temporarily removed
import { Crypto } from '../utils/types';

interface CryptoMenuItemProps {
  crypto: Crypto;
}

export const CryptoMenuItem: React.FC<CryptoMenuItemProps> = ({ crypto }) => {
  // const { data: cryptoStatus } = useCryptoStatus(crypto.id); // Temporarily removed

  return (
    <MenuItem key={crypto.id} value={crypto.id}>
      {crypto.name} ({crypto.symbol})
      {/* Icons temporarily removed for debugging */}
    </MenuItem>
  );
};
