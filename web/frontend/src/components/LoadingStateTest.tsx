'use client'

import React from 'react'
import { Box, Button, Typography, Paper, Alert } from '@mui/material'
import { useApiClient } from '../hooks/useApiClient.ts'

export const LoadingStateTest = () => {
  const { 
    getCryptos, 
    getStrategies, 
    healthCheck, 
    runAnalysis,
    isLoading 
  } = useApiClient()

  const testGetCryptos = async () => {
    try {
      console.log('Testing getCryptos - Loading should be TRUE')
      const result = await getCryptos()
      console.log('getCryptos result:', result)
    } catch (error) {
      console.error('getCryptos error:', error)
    }
  }

  const testGetStrategies = async () => {
    try {
      console.log('Testing getStrategies - Loading should be TRUE')
      const result = await getStrategies()
      console.log('getStrategies result:', result)
    } catch (error) {
      console.error('getStrategies error:', error)
    }
  }

  const testHealthCheck = async () => {
    try {
      console.log('Testing healthCheck - Loading should be TRUE')
      const result = await healthCheck()
      console.log('healthCheck result:', result)
    } catch (error) {
      console.error('healthCheck error:', error)
    }
  }

  const testRunAnalysis = async () => {
    try {
      console.log('Testing runAnalysis - Loading should be TRUE')
      const result = await runAnalysis({
        crypto_id: 'bitcoin',
        strategy_name: 'EMA_Only',
        timeframe: 24
      })
      console.log('runAnalysis result:', result)
    } catch (error) {
      console.error('runAnalysis error:', error)
    }
  }

  const testLongOperation = async () => {
    try {
      console.log('Testing long operation - Loading should be TRUE for 3 seconds')
      // Simulate a longer operation
      await new Promise(resolve => setTimeout(resolve, 3000))
      await healthCheck()
      console.log('Long operation completed')
    } catch (error) {
      console.error('Long operation error:', error)
    }
  }

  return (
    <Paper sx={{ p: 3, m: 2 }}>
      <Typography variant="h5" gutterBottom>
        API Loading State Test Component
      </Typography>
      
      <Alert severity="info" sx={{ mb: 2 }}>
        Current API Loading State: <strong>{isLoading ? 'TRUE' : 'FALSE'}</strong>
      </Alert>

      <Typography variant="body2" sx={{ mb: 2 }}>
        Click the buttons below to test API calls. Watch the loading state above and check the browser console for logs.
      </Typography>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Button 
          variant="contained" 
          onClick={testGetCryptos}
          disabled={isLoading}
        >
          Test Get Cryptos
        </Button>

        <Button 
          variant="contained" 
          onClick={testGetStrategies}
          disabled={isLoading}
        >
          Test Get Strategies
        </Button>

        <Button 
          variant="contained" 
          onClick={testHealthCheck}
          disabled={isLoading}
        >
          Test Health Check
        </Button>

        <Button 
          variant="contained" 
          onClick={testRunAnalysis}
          disabled={isLoading}
        >
          Test Run Analysis
        </Button>

        <Button 
          variant="outlined" 
          onClick={testLongOperation}
          disabled={isLoading}
        >
          Test Long Operation (3s delay)
        </Button>
      </Box>

      <Typography variant="caption" sx={{ mt: 2, display: 'block' }}>
        Instructions:
        <br />• Open browser developer tools (F12) and go to Console tab
        <br />• Click any button above
        <br />• Watch the "Current API Loading State" change to TRUE during the operation
        <br />• Check console logs for operation details
        <br />• Loading state should return to FALSE when operation completes
      </Typography>
    </Paper>
  )
}
