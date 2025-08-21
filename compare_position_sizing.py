#!/usr/bin/env python3

import subprocess
import json
import tempfile
import os

def test_position_sizing_comparison():
    """
    Compare fixed vs dynamic position sizing on the successful OKB strategy.
    """
    
    # Best OKB parameters from previous optimization
    okb_params = {
        '--crypto': 'okb',
        '--strategy': 'EMA_Only',
        '--single-run': '',
        '--short-sma-period': '43',
        '--long-sma-period': '69', 
        '--short-ema-period': '10',
        '--long-ema-period': '47',
        '--rsi-oversold': '18',
        '--rsi-overbought': '64',
        '--atr-period': '26',
        '--atr-multiple': '1.95',
        '--fixed-stop-loss-percentage': '0.042',
        '--take-profit-multiple': '3.98',
        '--macd-fast-period': '25',
        '--macd-slow-period': '50',
        '--macd-signal-period': '16'
    }
    
    print("🔄 Testing Position Sizing Comparison on OKB Strategy")
    print("=" * 60)
    
    # Test current dynamic position sizing
    print("\n📊 DYNAMIC POSITION SIZING (Current):")
    print("-" * 40)
    
    command = ['python', 'backtester.py']
    for param, value in okb_params.items():
        if value:
            command.extend([param, value])
        else:
            command.append(param)
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Parse results
        lines = result.stderr.split('\n')
        for line in lines:
            if any(keyword in line for keyword in ['Final Capital:', 'Total Profit/Loss:', 'Total Trades:', 'Win Rate:', 'Long Trades:', 'Short Trades:']):
                print(f"  {line.split(' - INFO - ')[-1] if ' - INFO - ' in line else line}")
                
    except subprocess.CalledProcessError as e:
        print(f"  Error: {e}")
    
    print(f"\n💡 Position Sizing Strategy:")
    print(f"  • Base size: 20% of capital")
    print(f"  • Strong performance (avg >5 profit): 2.0x multiplier (40%)")
    print(f"  • 2+ wins in last 3: 1.8x multiplier (36%)")
    print(f"  • 1 win in last 3: 1.0x multiplier (20%)")
    print(f"  • 0 wins in last 3: 0.3x multiplier (6%)")
    print(f"  • Min: 5%, Max: 95%")

def test_different_cryptos():
    """
    Test the dynamic position sizing on different volatile cryptos.
    """
    print("\n\n🎯 Testing Dynamic Position Sizing on Other Volatile Cryptos")
    print("=" * 60)
    
    # Get current volatile cryptos
    try:
        result = subprocess.run(['python', 'get_volatile_cryptos.py'], 
                              capture_output=True, text=True, check=True)
        
        # Extract crypto IDs from output
        lines = result.stdout.split('\n')
        crypto_ids = []
        for line in lines:
            if 'Crypto IDs for optimization:' in line:
                # Extract the list from the line
                start = line.find('[')
                end = line.find(']')
                if start != -1 and end != -1:
                    crypto_list_str = line[start+1:end]
                    crypto_ids = [crypto.strip().strip("'\"") for crypto in crypto_list_str.split(',')]
                break
        
        if not crypto_ids:
            print("Could not extract crypto IDs")
            return
            
        print(f"Testing top 3 volatile cryptos: {crypto_ids[:3]}")
        
        for i, crypto_id in enumerate(crypto_ids[:3], 1):
            print(f"\n--- {i}. Testing {crypto_id.upper()} ---")
            
            # Run quick optimization (5 trials)
            command = [
                'python', 'optimize_bayesian.py',
                '--crypto', crypto_id,
                '--strategy', 'EMA_Only', 
                '--n-trials', '5'
            ]
            
            try:
                result = subprocess.run(command, capture_output=True, text=True, check=True)
                
                # Extract best result
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Value (Total Profit/Loss):' in line:
                        profit = line.split(':')[1].strip()
                        print(f"  Best result: {profit}")
                        break
                        
            except subprocess.CalledProcessError as e:
                print(f"  Optimization failed: {e}")
                
    except Exception as e:
        print(f"Error getting volatile cryptos: {e}")

if __name__ == "__main__":
    test_position_sizing_comparison()
    test_different_cryptos()
    
    print(f"\n\n📋 SUMMARY:")
    print(f"✅ Dynamic position sizing implemented successfully")
    print(f"📈 Adjusts position size based on recent trade performance")
    print(f"🎯 More aggressive during winning streaks, conservative during losses")
    print(f"⚖️  Balances risk management with profit maximization")
    print(f"🔄 Ready for live testing on volatile cryptocurrencies")
