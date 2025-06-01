import os
import sys

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from stock_monitoring_app.backtest.backtest import BackTest
from stock_monitoring_app.config import settings # To check API keys

def run_stock_backtest_example():
    print("\n--- Running Stock BackTest Example (AAPL) ---")
    if not settings.POLYGON_API_KEY:
        print("POLYGON_API_KEY not set. Skipping stock BackTest example.")
        print("Please set the POLYGON_API_KEY environment variable.")
        return

    try:
        # Using a shorter period for quicker example run
        # Note: Autodiscovery of indicators will use default params.
        # Parameter optimization is a placeholder in the current BackTest class.
        stock_bt = BackTest(ticker="AAPL", period="3mo", interval="1d")
        print(f"Initialized BackTest for {stock_bt.ticker}, Period: {stock_bt.period}, Interval: {stock_bt.interval}")
        
        results_df = stock_bt.run_backtest()

        if results_df is not None and not results_df.empty:
            print(f"\nBacktest for {stock_bt.ticker} completed.")
            print("Performance Metrics:")
            for key, value in stock_bt.get_performance_metrics().items():
                print(f"  {key}: {value}")
            
            print("\nSample of Results DataFrame (last 5 rows):")
            # Show a subset of columns for brevity
            cols_to_show = [col for col in results_df.columns if 'Signal' in col or col == 'Close']
            if not cols_to_show or 'Close' not in cols_to_show : cols_to_show = ['Close'] + cols_to_show # ensure Close is there
            cols_to_show = list(dict.fromkeys(cols_to_show)) # Remove duplicates, preserve order (approx)
            
            print(results_df[cols_to_show].tail())
            print(f"\nFull results and metrics saved to 'backtest_outputs/{stock_bt.ticker}_...'")
        elif results_df is not None and results_df.empty:
             print(f"Backtest for {stock_bt.ticker} ran but produced an empty results DataFrame.")
        else:
            print(f"Backtest for {stock_bt.ticker} did not produce results (returned None). Check logs for errors.")

    except ValueError as ve: # Catch config errors for Polygon
        print(f"Configuration error for stock BackTest: {ve}")
    except Exception as e:
        print(f"An error occurred during the stock BackTest example: {e}")
        import traceback        
        traceback.print_exc()


def run_crypto_backtest_example():
    print("\n--- Running Crypto BackTest Example (Bitcoin) ---")
    # CoinGecko API key is optional.
    if not settings.COINGECKO_API_KEY:
        print("COINGECKO_API_KEY not set. Proceeding with public CoinGecko API for crypto BackTest (rate limits may apply).")

    try:
        crypto_bt = BackTest(ticker="bitcoin", period="3mo", interval="1d")
        print(f"Initialized BackTest for {crypto_bt.ticker}, Period: {crypto_bt.period}, Interval: {crypto_bt.interval}")

        results_df = crypto_bt.run_backtest()

        if results_df is not None and not results_df.empty:
            print(f"\nBacktest for {crypto_bt.ticker} completed.")
            print("Performance Metrics:")
            for key, value in crypto_bt.get_performance_metrics().items():
                print(f"  {key}: {value}")

            print("\nSample of Results DataFrame (last 5 rows):")
            cols_to_show = [col for col in results_df.columns if 'Signal' in col or col == 'Close']
            if not cols_to_show or 'Close' not in cols_to_show : cols_to_show = ['Close'] + cols_to_show
            cols_to_show = list(dict.fromkeys(cols_to_show))
            
            print(results_df[cols_to_show].tail())
            print(f"\nFull results and metrics saved to 'backtest_outputs/{crypto_bt.ticker}_...'")
        elif results_df is not None and results_df.empty:
             print(f"Backtest for {crypto_bt.ticker} ran but produced an empty results DataFrame.")
        else:
            print(f"Backtest for {crypto_bt.ticker} did not produce results (returned None). Check logs for errors.")
            
    except Exception as e:
        print(f"An error occurred during the crypto BackTest example: {e}")
        import traceback        
        traceback.print_exc()

if __name__ == "__main__":
    print("Running BackTest examples...")
    print("Ensure API keys are configured (POLYGON_API_KEY is required for stock example).")
    print("These examples will fetch live data and may take some time.")
    
    run_stock_backtest_example()
    run_crypto_backtest_example()

    print("\nBackTest examples completed.")    
    print("Check the 'backtest_outputs' directory for CSV and JSON files.")
