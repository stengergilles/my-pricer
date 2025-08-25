# API Loading State Fix

## Problem
The frontend was showing "API Loading: False" even when API operations were in progress.

## Root Cause
The `useApiClient` hook had incorrect method implementations:
1. The `post`, `get`, `put`, `del` methods were trying to call non-existent methods on the ApiClient
2. The `callApi` function was not properly handling the loading state due to method call failures
3. Components were calling `get('getCryptos')` instead of the actual `getCryptos` method

## Solution
1. **Updated `useApiClient` hook** to expose direct method calls instead of generic `get`/`post` methods
2. **Fixed method mapping** to properly call ApiClient methods like `getCryptos`, `runAnalysis`, etc.
3. **Updated components** to use the new method names:
   - `get('getCryptos')` → `getCryptos()`
   - `post('runAnalysis', data)` → `runAnalysis(data)`
   - `post('runBacktest', data)` → `runBacktest(data)`

## Changes Made

### `/hooks/useApiClient.ts`
- Replaced generic `get`, `post`, `put`, `del` methods with specific API method calls
- Added proper error handling in `callApi` function
- Ensured `setIsLoading(true)` is called at start and `setIsLoading(false)` in finally block

### `/components/CryptoAnalysis.tsx`
- Updated to use `getCryptos`, `getStrategies`, `getConfig`, `runAnalysis` methods
- Fixed query functions to call methods directly instead of through generic `get`

### `/components/BacktestRunner.tsx`
- Updated to use `getCryptos`, `getStrategies`, `getConfig`, `runBacktest` methods
- Fixed mutation to call `runBacktest` directly

### `/components/HealthStatus.tsx`
- Updated to use `healthCheck` method directly

## Testing
The loading state should now properly show "API Loading: True" when any API operation is in progress and "API Loading: False" when idle.

## Key Insight
The issue was that the hook was trying to call methods that didn't exist on the ApiClient, causing the API calls to fail silently and the loading state to never be properly managed.
