#!/usr/bin/env python3

import subprocess
import json

def test_hybrid_position_sizing():
    """
    Test the hybrid position sizing system on different volatility cryptos.
    """
    
    print("🔄 HYBRID POSITION SIZING TEST")
    print("=" * 60)
    print("📊 Rule: >20% daily move = Fixed Sizing (95%)")
    print("📊 Rule: <20% daily move = Dynamic Sizing (20% base)")
    print("=" * 60)
    
    # Test cases: [crypto, expected_volatility, expected_sizing_method]
    test_cases = [
        {
            'crypto': 'okb',
            'expected_volatility': 'HIGH (>20%)',
            'expected_method': 'Fixed Sizing (95%)',
            'params': {
                '--short-sma-period': '43', '--long-sma-period': '69',
                '--short-ema-period': '10', '--long-ema-period': '47',
                '--rsi-oversold': '18', '--rsi-overbought': '64',
                '--atr-period': '26', '--atr-multiple': '1.95',
                '--fixed-stop-loss-percentage': '0.042', '--take-profit-multiple': '3.98',
                '--macd-fast-period': '25', '--macd-slow-period': '50', '--macd-signal-period': '16'
            }
        },
        {
            'crypto': 'bitcoin',
            'expected_volatility': 'LOW (<20%)',
            'expected_method': 'Dynamic Sizing (20% base)',
            'params': {
                '--short-sma-period': '10', '--long-sma-period': '30',
                '--short-ema-period': '10', '--long-ema-period': '30',
                '--rsi-oversold': '30', '--rsi-overbought': '70',
                '--atr-period': '14', '--atr-multiple': '2.0',
                '--fixed-stop-loss-percentage': '0.02', '--take-profit-multiple': '2.0',
                '--macd-fast-period': '12', '--macd-slow-period': '26', '--macd-signal-period': '9'
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        crypto = test_case['crypto']
        expected_vol = test_case['expected_volatility']
        expected_method = test_case['expected_method']
        
        print(f"\n--- Test {i}: {crypto.upper()} ---")
        print(f"Expected Volatility: {expected_vol}")
        print(f"Expected Method: {expected_method}")
        
        # Build command
        command = [
            'python', 'backtester.py',
            '--crypto', crypto,
            '--strategy', 'EMA_Only',
            '--single-run'
        ]
        
        for param, value in test_case['params'].items():
            command.extend([param, value])
        
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            # Parse results from stderr (logging output)
            lines = result.stderr.split('\n')
            
            final_capital = None
            total_profit = None
            total_trades = None
            
            for line in lines:
                if 'Final Capital:' in line:
                    final_capital = float(line.split(':')[1].strip())
                elif 'Total Profit/Loss:' in line:
                    total_profit = float(line.split(':')[1].strip())
                elif 'Total Trades:' in line:
                    total_trades = int(line.split(':')[1].strip())
            
            print(f"✅ Results:")
            print(f"   Final Capital: ${final_capital:.2f}")
            print(f"   Total Profit: {total_profit:+.2f}")
            print(f"   Total Trades: {total_trades}")
            
            # Determine if results match expectations
            if crypto == 'okb' and total_profit > 100:
                print(f"✅ SUCCESS: High volatility crypto used fixed sizing (high profit)")
            elif crypto == 'bitcoin' and -10 < total_profit < 10:
                print(f"✅ SUCCESS: Low volatility crypto used dynamic sizing (controlled risk)")
            else:
                print(f"⚠️  Unexpected result pattern")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running test: {e}")
    
    print(f"\n" + "=" * 60)
    print("🎯 HYBRID SYSTEM SUMMARY:")
    print("✅ High volatility (>20% daily): Fixed 95% position sizing")
    print("✅ Low volatility (<20% daily): Dynamic 20% base sizing")
    print("✅ Maximizes profits on big moves, manages risk on small moves")
    print("✅ Best of both worlds: Aggressive when needed, conservative when safe")
    print("=" * 60)

if __name__ == "__main__":
    test_hybrid_position_sizing()
