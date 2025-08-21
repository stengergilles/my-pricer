import requests
import pandas as pd
import argparse
import os
import json
import math
import time
import glob
from functools import reduce
import operator
from datetime import datetime, timedelta # Import datetime
import logging # Import logging module

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("debug.log"),
                        logging.StreamHandler()
                    ])
from lines import find_swing_points, calculate_line_equation, find_support_resistance_lines, analyze_line_durations, auto_discover_percentage_change, predict_next_move
from data import get_crypto_data
from indicators import calculate_sma, calculate_ema, calculate_rsi, calculate_macd, calculate_bbands, calculate_atr
from chart import generate_chart
from magnitude import predict_movement_magnitude
from config import backtest_configs, strategy_configs, ATR_PERIOD, ATR_MULTIPLE, DEFAULT_TIMEFRAME, DEFAULT_INTERVAL

# Import compatibility functions for new backtester system
from pricer_compatibility_fix import (
    find_best_result_file,
    normalize_result_data,
    calculate_hybrid_position_size,
    load_strategy_config,
    get_daily_volatility
)

SAVE_INTERVAL_MINUTES = 60 # Save results every 60 minutes

def get_current_price(crypto_id):
    """Fetches the current price of a crypto from CoinGecko."""
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data[crypto_id]['usd']
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching current price for {crypto_id}: {e}")
        return None

class LiveTrader:
    def __init__(self, crypto_id, initial_capital, trade_size_percentage, strategy_config, params, simulation_start_time, win_rate, spread_percentage, slippage_percentage, intermediate_stop_loss_percentage, best_config_name):
        self.crypto_id = crypto_id
        self.initial_capital = initial_capital # Store initial capital
        self.current_capital = initial_capital
        self.trade_size_percentage = trade_size_percentage
        self.base_trade_size = trade_size_percentage  # Store original size for hybrid sizing
        self.strategy_config = strategy_config
        self.params = params
        self.simulation_start_time = simulation_start_time # Store the start time of the simulation
        self.win_rate = win_rate # Store the win rate
        self.spread_percentage = spread_percentage
        self.slippage_percentage = slippage_percentage
        self.position = None  # None, 'LONG', 'SHORT'
        self.entry_price = 0.0
        self.entry_timestamp = None
        self.trade_history = []
        self.win_trades = 0
        self.lost_trades = 0
        self.num_trades = 0
        self.df_history = pd.DataFrame() # To store recent data for indicator calculation
        self.trailing_stop_loss = 0.0 # New: Trailing stop loss level
        self.highest_price_since_entry = 0.0 # New: For long positions
        self.lowest_price_since_entry = 0.0  # New: For short positions
        self.allocated_capital = 0.0 # Capital currently in open positions
        self.entry_position_size = 0.0 # Size of the current open position
        self.intermediate_stop_loss_percentage = intermediate_stop_loss_percentage
        self.best_config_name = best_config_name
        self.last_save_time = datetime.now()
        # New: Track recent trades for hybrid position sizing
        self.recent_trade_results = []  # Track recent trade P/L for dynamic sizing

    def update_position_sizing(self):
        """Update position sizing based on recent performance and volatility."""
        new_size = calculate_hybrid_position_size(
            self.crypto_id, 
            self.base_trade_size, 
            self.recent_trade_results
        )
        self.trade_size_percentage = new_size
        logging.info(f"Updated position size to: {new_size:.1%} (volatility-based hybrid sizing)")
        
        # Log reasoning
        daily_vol = get_daily_volatility(self.crypto_id)
        if daily_vol > 0.20:
            logging.info(f"  High volatility ({daily_vol:.1%}) → Fixed aggressive sizing (95%)")
        else:
            recent_wins = sum(1 for trade in self.recent_trade_results[-3:] if trade > 0) if len(self.recent_trade_results) >= 3 else 0
            logging.info(f"  Low volatility ({daily_vol:.1%}) → Dynamic sizing (recent wins: {recent_wins}/3)")
        self.spread_percentage = spread_percentage
        self.slippage_percentage = slippage_percentage
        self.position = None  # None, 'LONG', 'SHORT'
        self.entry_price = 0.0
        self.entry_timestamp = None
        self.trade_history = []
        self.win_trades = 0
        self.lost_trades = 0
        self.num_trades = 0
        self.df_history = pd.DataFrame() # To store recent data for indicator calculation
        self.trailing_stop_loss = 0.0 # New: Trailing stop loss level
        self.highest_price_since_entry = 0.0 # New: For long positions
        self.lowest_price_since_entry = 0.0  # New: For short positions
        self.allocated_capital = 0.0 # Capital currently in open positions
        self.entry_position_size = 0.0 # Size of the current open position
        self.intermediate_stop_loss_percentage = intermediate_stop_loss_percentage
        self.best_config_name = best_config_name
        self.last_save_time = datetime.now()

    def fetch_latest_data(self):
        logging.info(f"Fetching latest data for {self.crypto_id} from coingecko...")
        
        ohlc_data = get_crypto_data(self.crypto_id, 1)
        
        if not ohlc_data:
            logging.error(f"Could not fetch data for {self.crypto_id} from coingecko. Skipping live trade step.")
            return False
        logging.info(f"Successfully fetched data for {self.crypto_id} from coingecko.")

        df_new = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'price'])
        df_new['timestamp'] = pd.to_datetime(df_new['timestamp'], unit='ms')
        df_new.set_index('timestamp', inplace=True)
        
        # Add 'close' column for compatibility with indicators
        df_new['close'] = df_new['price']

        # Calculate bid and ask prices based on the spread (applies to both sources)
        df_new['ask_price'] = df_new['price'] * (1 + self.spread_percentage)
        df_new['bid_price'] = df_new['price'] * (1 - self.spread_percentage)

        self.df_history = pd.concat([self.df_history, df_new]).drop_duplicates().sort_index().tail(100) # Keep last 100 bars
        return True

    def execute_trade_step(self):
        

        if not self.fetch_latest_data():
            return False # Indicate that monitoring was refused (due to data fetch failure)

        if self.df_history.empty:
            logging.info("Not enough historical data to make a trade decision.")
            return

        signal = get_trade_signal(self.df_history, self.strategy_config, self.params)
        current_price = self.df_history['price'].iloc[-1] # Keep for display/logging if needed
        current_ask_price = self.df_history['ask_price'].iloc[-1]
        current_bid_price = self.df_history['bid_price'].iloc[-1]
        timestamp = self.df_history.index[-1]

        logging.info(f"\n--- Live Trade Step at {timestamp} ---")
        logging.info(f"Current Price: {current_price:.8f}")
        logging.info(f"Current Signal: {signal}")
        logging.info(f"Current Capital: {self.current_capital:.2f}")
        logging.info(f"Current Position Size: {self.entry_position_size:.4f}")
        if self.entry_price != 0:
            current_profit = (current_price - self.entry_price) / self.entry_price * self.entry_position_size
            logging.info(f"Current Position P/L: {current_profit:.4f}")
        else:
            logging.info(f"Current Position P/L: 0.0000")
        logging.info(f"Invested Size: {self.allocated_capital:.4f}")
        logging.info(f"Current Position: {self.position}")

        
        # Calculate ATR
        current_atr = calculate_atr(self.df_history, ATR_PERIOD).iloc[-1] if not self.df_history.empty else 0.0

        # Update trailing stop loss for open positions
        if self.position == "LONG":
            if current_price > self.highest_price_since_entry:
                self.highest_price_since_entry = current_price
            # The trailing stop loss should only move down for a long position
            # It is set ATR_MULTIPLE below the highest price reached since entry
            calculated_stop_loss = self.highest_price_since_entry - (current_atr * ATR_MULTIPLE)
            if calculated_stop_loss < self.trailing_stop_loss: # Only move stop down
                self.trailing_stop_loss = calculated_stop_loss
            logging.info(f"  Trailing Stop Loss (LONG): {self.trailing_stop_loss:.8f}")
            if current_price <= self.trailing_stop_loss and current_atr > 0: # Exit if stop hit
                signal = "SHORT" # Force exit
                logging.info(f"  ACTION: Trailing Stop Loss hit for LONG position!")

        elif self.position == "SHORT":
            if current_price < self.lowest_price_since_entry:
                self.lowest_price_since_entry = current_price
            # The trailing stop loss should only move up for a short position
            # It is set ATR_MULTIPLE above the lowest price reached since entry
            calculated_stop_loss = self.lowest_price_since_entry + (current_atr * ATR_MULTIPLE)
            if calculated_stop_loss > self.trailing_stop_loss: # Only move stop up
                self.trailing_stop_loss = calculated_stop_loss
            logging.info(f"  Trailing Stop Loss (SHORT): {self.trailing_stop_loss:.8f}")
            if current_price >= self.trailing_stop_loss and current_atr > 0: # Exit if stop hit
                signal = "LONG" # Force exit
                logging.info(f"  ACTION: Trailing Stop Loss hit for SHORT position!")

        # Calculate and display current indicator values
        short_sma = calculate_sma(self.df_history, self.params['short_sma_period']).iloc[-1]
        long_sma = calculate_sma(self.df_history, self.params['long_sma_period']).iloc[-1]
        rsi = calculate_rsi(self.df_history).iloc[-1]
        
        
        
        macd_data = calculate_macd(self.df_history, self.params['macd_fast_period'], self.params['macd_slow_period'], self.params['macd_signal_period'])
        macd = macd_data['MACD'].iloc[-1]
        signal_line = macd_data['Signal'].iloc[-1]
        bbands = calculate_bbands(self.df_history)
        bb_hband = bbands['bb_hband'].iloc[-1]
        bb_lband = bbands['bb_lband'].iloc[-1]

        logging.info(f"  Indicators:")
        logging.info(f"    SMA: Short={short_sma:.8f}, Long={long_sma:.8f}")
        
        # Add EMA display
        short_ema = calculate_ema(self.df_history, self.params['short_sma_period']).iloc[-1]
        long_ema = calculate_ema(self.df_history, self.params['long_sma_period']).iloc[-1]
        logging.info(f"    EMA: Short={short_ema:.8f}, Long={long_ema:.8f}")

        logging.info(f"    RSI: {rsi:.2f}")
        logging.info(f"    MACD: MACD={macd:.8f}, Signal={signal_line:.8f}")
        logging.info(f"    Bollinger Bands: Upper={bb_hband:.8f}, Lower={bb_lband:.8f}")
        logging.info(f"    ATR: {current_atr:.8f}")

        if self.position is None:
            if signal == "LONG":
                self.position = "LONG"
                self.entry_price = current_ask_price * (1 + self.slippage_percentage) # Buy at ask price with slippage
                self.entry_timestamp = timestamp
                self.num_trades += 1
                self.highest_price_since_entry = current_ask_price # Initialize for trailing stop
                self.trailing_stop_loss = self.highest_price_since_entry - (current_atr * ATR_MULTIPLE) # Initial stop
                
                # Deduct position size from current_capital and add to allocated_capital
                self.entry_position_size = self.current_capital * self.trade_size_percentage
                self.current_capital -= self.entry_position_size
                self.allocated_capital += self.entry_position_size
                
                print(f"ACTION: Entered LONG at {self.entry_price:.2f} with size {self.entry_position_size:.2f}")
                self.monitor_intermediate_stops()
            elif signal == "SHORT":
                self.position = "SHORT"
                self.entry_price = current_bid_price * (1 - self.slippage_percentage) # Sell at bid price with slippage
                self.entry_timestamp = timestamp
                self.num_trades += 1
                self.lowest_price_since_entry = current_bid_price # Initialize for trailing stop
                self.trailing_stop_loss = self.lowest_price_since_entry + (current_atr * ATR_MULTIPLE) # Initial stop
                
                # Deduct position size from current_capital and add to allocated_capital
                self.entry_position_size = self.current_capital * self.trade_size_percentage
                self.current_capital -= self.entry_position_size
                self.allocated_capital += self.entry_position_size
                
                print(f"ACTION: Entered SHORT at {self.entry_price:.2f} with size {self.entry_position_size:.2f}")
                self.monitor_intermediate_stops()
        elif self.position == "LONG":
            if signal == "SHORT": # Exit long on short signal
                exit_price = current_bid_price * (1 - self.slippage_percentage) # Sell at bid price with slippage
                profit_loss = (exit_price - self.entry_price) / self.entry_price * self.entry_position_size # Calculate P/L based on entry_position_size
                
                # Reconcile capital
                self.current_capital += (self.entry_position_size + profit_loss)
                self.allocated_capital -= self.entry_position_size # Remove from allocated capital
                
                self.trade_history.append({
                    'type': 'LONG',
                    'entry_price': self.entry_price,
                    'exit_price': exit_price,
                    'profit_loss': profit_loss,
                    'entry_time': self.entry_timestamp,
                    'exit_time': timestamp,
                    'capital_after_trade': self.current_capital # This will now be the total capital
                })
                if profit_loss > 0:
                    self.win_trades += 1
                else:
                    self.lost_trades += 1
                
                # Update recent trades for hybrid position sizing
                self.recent_trade_results.append(profit_loss)
                if len(self.recent_trade_results) > 5:  # Keep only last 5 trades
                    self.recent_trade_results.pop(0)
                self.update_position_sizing()  # Update sizing after each trade
                
                self.position = None
                self.entry_position_size = 0.0 # Reset
                self.highest_price_since_entry = 0.0 # Reset for next trade
                self.trailing_stop_loss = 0.0 # Reset for next trade
                print(f"ACTION: Exited LONG at {exit_price:.2f}, P/L: {profit_loss:.2f}, New Capital: {self.current_capital:.2f}")
                self.save_results() # Save results after trade exit
        elif self.position == "SHORT":
            if signal == "LONG": # Exit short on long signal
                exit_price = current_ask_price * (1 + self.slippage_percentage) # Buy back at ask price with slippage
                profit_loss = (self.entry_price - exit_price) / self.entry_price * self.entry_position_size # Calculate P/L based on entry_position_size
                
                # Reconcile capital
                self.current_capital += (self.entry_position_size + profit_loss)
                self.allocated_capital -= self.entry_position_size # Remove from allocated capital
                
                self.trade_history.append({
                    'type': 'SHORT',
                    'entry_price': self.entry_price,
                    'exit_price': exit_price,
                    'profit_loss': profit_loss,
                    'entry_time': self.entry_timestamp,
                    'exit_time': timestamp,
                    'capital_after_trade': self.current_capital # This will now be the total capital
                })
                if profit_loss > 0:
                    self.win_trades += 1
                else:
                    self.lost_trades += 1
                
                # Update recent trades for hybrid position sizing
                self.recent_trade_results.append(profit_loss)
                if len(self.recent_trade_results) > 5:  # Keep only last 5 trades
                    self.recent_trade_results.pop(0)
                self.update_position_sizing()  # Update sizing after each trade
                
                self.position = None
                self.entry_position_size = 0.0 # Reset
                self.lowest_price_since_entry = 0.0 # Reset for next trade
                self.trailing_stop_loss = 0.0 # Reset for next trade
                print(f"ACTION: Exited SHORT at {exit_price:.2f}, P/L: {profit_loss:.2f}, New Capital: {self.current_capital:.2f}")
                self.save_results() # Save results after trade exit

        print(f"Total Trades: {self.num_trades}, Wins: {self.win_trades}, Losses: {self.lost_trades}")
        print(f"Current Capital: {self.current_capital:.2f}")

        # Periodic save
        if (datetime.now() - self.last_save_time) > timedelta(minutes=SAVE_INTERVAL_MINUTES):
            self.save_results()
            self.last_save_time = datetime.now()
            logging.info(f"Periodic save triggered at {self.last_save_time.strftime('%Y-%m-%d %H:%M:%S')}")

        return True # Indicate that trade step was executed

    def monitor_intermediate_stops(self):
        if self.position is None:
            return

        stop_loss_price = 0
        take_profit_price = 0

        if self.position == 'LONG':
            stop_loss_price = self.entry_price * (1 - self.intermediate_stop_loss_percentage)
            take_profit_price = self.entry_price * (1 + self.intermediate_stop_loss_percentage)
        elif self.position == 'SHORT':
            stop_loss_price = self.entry_price * (1 + self.intermediate_stop_loss_percentage)
            take_profit_price = self.entry_price * (1 - self.intermediate_stop_loss_percentage)

        end_time = datetime.now() + timedelta(minutes=30)
        while datetime.now() < end_time:
            current_price = get_current_price(self.crypto_id)
            if current_price is None:
                time.sleep(60)
                continue

            logging.info(f"Intermediate check: Current price: {current_price:.8f}, SL: {stop_loss_price:.8f}, TP: {take_profit_price:.8f}")

            if self.position == 'LONG':
                if current_price <= stop_loss_price or current_price >= take_profit_price:
                    self.position = None
                    exit_price = current_price * (1 - self.slippage_percentage)
                    profit_loss = (exit_price - self.entry_price) / self.entry_price * self.entry_position_size
                    self.current_capital += (self.entry_position_size + profit_loss)
                    self.allocated_capital -= self.entry_position_size
                    self.trade_history.append({
                        'type': 'LONG',
                        'entry_price': self.entry_price,
                        'exit_price': exit_price,
                        'profit_loss': profit_loss,
                        'entry_time': self.entry_timestamp,
                        'exit_time': datetime.now(),
                        'capital_after_trade': self.current_capital
                    })
                    if profit_loss > 0:
                        self.win_trades += 1
                    else:
                        self.lost_trades += 1
                    
                    # Update recent trades for hybrid position sizing
                    self.recent_trade_results.append(profit_loss)
                    if len(self.recent_trade_results) > 5:
                        self.recent_trade_results.pop(0)
                    self.update_position_sizing()
                    
                    print(f"ACTION: Exited LONG at {exit_price:.2f}, P/L: {profit_loss:.2f}, New Capital: {self.current_capital:.2f}")
                    break
            elif self.position == 'SHORT':
                if current_price >= stop_loss_price or current_price <= take_profit_price:
                    self.position = None
                    exit_price = current_price * (1 + self.slippage_percentage)
                    profit_loss = (self.entry_price - exit_price) / self.entry_price * self.entry_position_size
                    self.current_capital += (self.entry_position_size + profit_loss)
                    self.allocated_capital -= self.entry_position_size
                    self.trade_history.append({
                        'type': 'SHORT',
                        'entry_price': self.entry_price,
                        'exit_price': exit_price,
                        'profit_loss': profit_loss,
                        'entry_time': self.entry_timestamp,
                        'exit_time': datetime.now(),
                        'capital_after_trade': self.current_capital
                    })
                    if profit_loss > 0:
                        self.win_trades += 1
                    else:
                        self.lost_trades += 1
                    
                    # Update recent trades for hybrid position sizing
                    self.recent_trade_results.append(profit_loss)
                    if len(self.recent_trade_results) > 5:
                        self.recent_trade_results.pop(0)
                    self.update_position_sizing()
                    
                    print(f"ACTION: Exited SHORT at {exit_price:.2f}, P/L: {profit_loss:.2f}, New Capital: {self.current_capital:.2f}")
                    break
            time.sleep(60)

    def save_results(self):
        current_end_time = datetime.now()
        start_date_str = self.simulation_start_time.strftime("%Y%m%d_%H%M%S")
        end_date_str = current_end_time.strftime("%Y%m%d_%H%M%S")
        
        results_dir = os.path.join("live_results", self.crypto_id, f"{start_date_str}_to_{end_date_str}")
        os.makedirs(results_dir, exist_ok=True)

        results_filename = os.path.join(results_dir, "results.json")

        # Prepare data for saving
        data_to_save = {
            "initial_capital": self.initial_capital, # Need to store initial_capital in LiveTrader
            "final_capital": self.current_capital,
            "total_profit_loss": self.current_capital - self.initial_capital,
            "num_trades": self.num_trades,
            "win_trades": self.win_trades,
            "lost_trades": self.lost_trades,
            "win_rate": (self.win_trades / self.num_trades) * 100 if self.num_trades > 0 else 0,
            "trade_history": [{
                "type": trade['type'],
                "entry_price": trade['entry_price'],
                "exit_price": trade['exit_price'],
                "profit_loss": trade['profit_loss'],
                "entry_time": str(trade['entry_time']), # Convert timestamp to string for JSON
                "exit_time": str(trade['exit_time']),
                "capital_after_trade": trade['capital_after_trade']
            } for trade in self.trade_history]
        }

        with open(results_filename, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        print(f"Live simulation results saved to {results_filename}")


def get_trade_signal(df: pd.DataFrame, strategy_config: dict, params: dict):

    """
    Determines the trade signal for the latest data point.
    """
    df_copy = df.copy()

    # --- 1. Calculate all possible indicators and base signals ---
    base_signals = {}
    
    # Moving Averages
    short_sma = calculate_sma(df_copy, params['short_sma_period'])
    long_sma = calculate_sma(df_copy, params['long_sma_period'])
    short_ema = calculate_ema(df_copy, params['short_sma_period'])
    long_ema = calculate_ema(df_copy, params['long_sma_period'])
    
    base_signals['sma_crossover'] = (short_sma.shift(1) < long_sma.shift(1)) & (short_sma >= long_sma)
    base_signals['sma_crossunder'] = (short_sma.shift(1) > long_sma.shift(1)) & (short_sma <= long_sma)
    base_signals['ema_crossover'] = (short_ema.shift(1) < long_ema.shift(1)) & (short_ema >= long_ema)
    base_signals['ema_crossunder'] = (short_ema.shift(1) > long_ema.shift(1)) & (short_ema <= long_ema)

    # RSI
    rsi = calculate_rsi(df_copy)
    base_signals['rsi_is_not_overbought'] = rsi < params['rsi_overbought']
    base_signals['rsi_is_not_oversold'] = rsi > params['rsi_oversold']
    base_signals['rsi_is_overbought'] = rsi > params['rsi_overbought']
    base_signals['rsi_is_oversold'] = rsi < params['rsi_oversold']

    # MACD
    macd_data = calculate_macd(df_copy, params['macd_fast_period'], params['macd_slow_period'], params['macd_signal_period'])
    base_signals['macd_is_bullish'] = macd_data['MACD'] > macd_data['Signal']
    base_signals['macd_is_bearish'] = macd_data['MACD'] < macd_data['Signal']

    # Volume
    if 'volume' in df_copy.columns:
        volume_sma = df_copy['volume'].rolling(window=20).mean()
        base_signals['is_high_volume'] = df_copy['volume'] > volume_sma
    else:
        base_signals['is_high_volume'] = pd.Series(True, index=df_copy.index)


    # Bollinger Bands
    bbands = calculate_bbands(df_copy)
    base_signals['price_breaks_upper_band'] = df_copy['price'] > bbands['bb_hband']
    base_signals['price_breaks_lower_band'] = df_copy['price'] < bbands['bb_lband']
    base_signals['price_crosses_middle_band_from_top'] = (df_copy['price'].shift(1) > bbands['bb_mavg'].shift(1)) & (df_copy['price'] <= bbands['bb_mavg'])
    base_signals['price_crosses_middle_band_from_bottom'] = (df_copy['price'].shift(1) < bbands['bb_mavg'].shift(1)) & (df_copy['price'] >= bbands['bb_mavg'])

    # Combined OR signals for new strategy
    base_signals['all_triggers_long_or'] = (
        base_signals['sma_crossover'] |
        base_signals['ema_crossover'] |
        base_signals['price_breaks_upper_band'] |
        base_signals['price_crosses_middle_band_from_bottom']
    )
    base_signals['all_triggers_short_or'] = (
        base_signals['sma_crossunder'] |
        base_signals['ema_crossunder'] |
        base_signals['price_breaks_lower_band'] |
        base_signals['price_crosses_middle_band_from_top']
    )
    base_signals['all_verificators_long_or'] = (
        base_signals['is_high_volume'] |
        base_signals['rsi_is_not_overbought']
    )
    base_signals['all_verificators_short_or'] = (
        base_signals['is_high_volume'] |
        base_signals['rsi_is_not_oversold']
    )

    # Combined OR signals for exit strategy
    base_signals['all_exits_long_or'] = (
        base_signals['sma_crossunder'] |
        base_signals['ema_crossunder'] |
        base_signals['price_crosses_middle_band_from_top'] |
        base_signals['rsi_is_overbought'] |
        base_signals['price_breaks_upper_band']
    )
    base_signals['all_exits_short_or'] = (
        base_signals['sma_crossover'] |
        base_signals['ema_crossover'] |
        base_signals['price_crosses_middle_band_from_bottom'] |
        base_signals['rsi_is_oversold'] |
        base_signals['price_breaks_lower_band']
    )

    # --- 2. Combine base signals based on the selected strategy ---
    def combine_signals(signal_names):
        signals_to_combine = [base_signals[name] for name in signal_names if name in base_signals]
        if not signals_to_combine:
            return pd.Series(False, index=df_copy.index)
        return reduce(operator.and_, signals_to_combine)

    long_entry_signals = combine_signals(strategy_config['long_entry'])
    short_entry_signals = combine_signals(strategy_config['short_entry'])

    # --- 3. Get the signal for the last data point ---
    if not long_entry_signals.empty and long_entry_signals.iloc[-1]:
        return "LONG"
    elif not short_entry_signals.empty and short_entry_signals.iloc[-1]:
        return "SHORT"
    else:
        return "HOLD"

def run_backtest_simulation(df: pd.DataFrame, strategy_config: dict, params: dict, initial_capital: float = 10000.0, trade_size_percentage: float = 0.1):
    """
    Simulates a backtest of a trading strategy.
    """
    # Calculate bid and ask prices for the entire DataFrame
    df['ask_price'] = df['price'] * (1 + params.get('spread_percentage', 0.01))
    df['bid_price'] = df['price'] * (1 - params.get('spread_percentage', 0.01))

    current_capital = initial_capital
    position = None  # None, 'LONG', or 'SHORT'
    entry_price = 0.0
    trade_history = []
    win_trades = 0
    lost_trades = 0
    num_trades = 0
    trailing_stop_loss = 0.0
    highest_price_since_entry = 0.0
    lowest_price_since_entry = 0.0
    allocated_capital = 0.0 # Capital currently in open positions
    entry_position_size = 0.0 # Size of the current open position
    fixed_stop_loss_price = 0.0 # New: Fixed stop loss level
    take_profit_price = 0.0 # New: Take profit level

    for i in range(len(df)):
        current_df_slice = df.iloc[:i+1]
        if current_df_slice.empty:
            continue

        signal = get_trade_signal(current_df_slice, strategy_config, params)
        current_price = df['price'].iloc[i] # Keep for display/logging if needed
        current_ask_price = df['ask_price'].iloc[i]
        current_bid_price = df['bid_price'].iloc[i]
        timestamp = df.index[i]

        # Calculate ATR for the current slice
        current_atr = 0.0
        if len(current_df_slice) > ATR_PERIOD: # Ensure enough data for ATR calculation
            current_atr = calculate_atr(current_df_slice, ATR_PERIOD).iloc[-1]

        # Update trailing stop loss for open positions
        if position == "LONG":
            if current_price > highest_price_since_entry:
                highest_price_since_entry = current_price
            calculated_stop_loss = highest_price_since_entry - (current_atr * ATR_MULTIPLE)
            if calculated_stop_loss < trailing_stop_loss: # Only move stop down
                trailing_stop_loss = calculated_stop_loss
            if current_price <= trailing_stop_loss and current_atr > 0: # Exit if stop hit
                signal = "SHORT" # Force exit

        elif position == "SHORT":
            if current_price < lowest_price_since_entry:
                lowest_price_since_entry = current_price
            calculated_stop_loss = lowest_price_since_entry + (current_atr * ATR_MULTIPLE)
            if calculated_stop_loss > trailing_stop_loss: # Only move stop up
                trailing_stop_loss = calculated_stop_loss
            if current_price >= trailing_stop_loss and current_atr > 0: # Exit if stop hit
                signal = "LONG" # Force exit

        # Check fixed stop loss and take profit for open positions
        if position == "LONG":
            if current_price <= fixed_stop_loss_price:
                signal = "SHORT" # Force exit due to stop loss
            elif current_price >= take_profit_price:
                signal = "SHORT" # Force exit due to take profit
        elif position == "SHORT":
            if current_price >= fixed_stop_loss_price:
                signal = "LONG" # Force exit due to stop loss
            elif current_price <= take_profit_price:
                signal = "LONG" # Force exit due to take profit

        if position is None:
            if signal == "LONG":
                position = "LONG"
                entry_price = current_ask_price * (1 + params.get('slippage_percentage', 0.0005)) # Buy at ask price with slippage
                num_trades += 1
                entry_timestamp = timestamp
                highest_price_since_entry = current_ask_price # Initialize for trailing stop
                trailing_stop_loss = highest_price_since_entry - (current_atr * ATR_MULTIPLE) # Initial stop
                
                # Calculate fixed stop loss and take profit for LONG
                fixed_stop_loss_price = entry_price * (1 - params.get('fixed_stop_loss_percentage', 0.02)) # Default 2% stop loss
                risk_amount = entry_price - fixed_stop_loss_price
                take_profit_price = entry_price + (risk_amount * params.get('take_profit_multiple', 1.5)) # Default 1.5x risk as profit

                # Deduct position size from current_capital and add to allocated_capital
                entry_position_size = current_capital * trade_size_percentage
                current_capital -= entry_position_size
                allocated_capital += entry_position_size
            elif signal == "SHORT":
                position = "SHORT"
                entry_price = current_bid_price * (1 - params.get('slippage_percentage', 0.0005)) # Sell at bid price with slippage
                num_trades += 1
                entry_timestamp = timestamp
                lowest_price_since_entry = current_bid_price # Initialize for trailing stop
                trailing_stop_loss = lowest_price_since_entry + (current_atr * ATR_MULTIPLE) # Initial stop
                
                # Calculate fixed stop loss and take profit for SHORT
                fixed_stop_loss_price = entry_price * (1 + params.get('fixed_stop_loss_percentage', 0.02)) # Default 2% stop loss
                risk_amount = fixed_stop_loss_price - entry_price
                take_profit_price = entry_price - (risk_amount * params.get('take_profit_multiple', 1.5)) # Default 1.5x risk as profit

                # Deduct position size from current_capital and add to allocated_capital
                entry_position_size = current_capital * trade_size_percentage
                current_capital -= entry_position_size
                allocated_capital += entry_position_size
        elif position == "LONG":
            if signal == "SHORT" or i == len(df) - 1: # Exit long on short signal or end of data
                exit_price = current_bid_price * (1 - params.get('slippage_percentage', 0.0005)) # Sell at bid price with slippage
                profit_loss = (exit_price - entry_price) / entry_price * entry_position_size # Calculate P/L based on entry_position_size
                
                # Reconcile capital
                current_capital += (entry_position_size + profit_loss)
                allocated_capital -= entry_position_size # Remove from allocated capital
                
                trade_history.append({
                    'type': 'LONG',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'profit_loss': profit_loss,
                    'entry_time': entry_timestamp,
                    'exit_time': timestamp,
                    'capital_after_trade': current_capital # This will now be the total capital
                })
                if profit_loss > 0:
                    win_trades += 1
                else:
                    lost_trades += 1
                position = None
                entry_position_size = 0.0 # Reset
                highest_price_since_entry = 0.0 # Reset for next trade
                trailing_stop_loss = 0.0 # Reset for next trade
                fixed_stop_loss_price = 0.0 # Reset for next trade
                take_profit_price = 0.0 # Reset for next trade
        elif position == "SHORT":
            if signal == "LONG" or i == len(df) - 1: # Exit short on long signal or end of data
                exit_price = current_ask_price * (1 + params.get('slippage_percentage', 0.0005)) # Buy back at ask price with slippage
                profit_loss = (entry_price - exit_price) / entry_price * entry_position_size # Calculate P/L based on entry_position_size
                
                # Reconcile capital
                current_capital += (entry_position_size + profit_loss)
                allocated_capital -= entry_position_size # Remove from allocated capital
                
                trade_history.append({
                    'type': 'SHORT',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'profit_loss': profit_loss,
                    'entry_time': entry_timestamp,
                    'exit_time': timestamp,
                    'capital_after_trade': current_capital # This will now be the total capital
                })
                if profit_loss > 0:
                    win_trades += 1
                else:
                    lost_trades += 1
                position = None
                entry_position_size = 0.0 # Reset
                lowest_price_since_entry = 0.0 # Reset for next trade
                trailing_stop_loss = 0.0 # Reset for next trade
                fixed_stop_loss_price = 0.0 # Reset for next trade
                take_profit_price = 0.0 # Reset for next trade

    total_profit = current_capital - initial_capital
    win_rate = (win_trades / num_trades) * 100 if num_trades > 0 else 0

    return {
        'final_capital': current_capital,
        'total_profit': total_profit,
        'num_trades': num_trades,
        'win_trades': win_trades,
        'lost_trades': lost_trades,
        'win_rate': win_rate,
        'trade_history': trade_history
    }

def run_analysis(crypto_id, param_set, for_live_trading=False):
    print(f"--- Analyzing latest backtest results for {crypto_id} ---")

    # Use different data amounts based on purpose
    if for_live_trading:
        days_to_fetch = 1  # Minimal data for live trading indicators
    else:
        days_to_fetch = 7  # More data for comprehensive charting
    
    print(f"Fetching {days_to_fetch} day(s) of data for {crypto_id} from coingecko...")
    ohlc_data = get_crypto_data(crypto_id, days_to_fetch)

    if not ohlc_data:
        print(f"Error: Could not fetch data for {crypto_id}. Exiting.")
        return None

    df = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # Add 'close' column for compatibility with indicators
    df['close'] = df['price']

    df_for_charting = df.copy()

    all_backtest_results = {}
    best_overall_params = None
    best_overall_win_rate = 0.0 # Initialize best overall win rate
    best_config_name = None
    best_strategy_name = 'Unknown'
    latest_backtest_timestamp = 0 # Initialize with a very old timestamp

    default_params = {
        'short_sma_period': 20, 'long_sma_period': 50,
        'rsi_overbought': 70, 'rsi_oversold': 30,
        'macd_fast_period': 12, 'macd_slow_period': 26, 'macd_signal_period': 9,
        'spread_percentage': 0.01, 'slippage_percentage': 0.0005,
        'fixed_stop_loss_percentage': 0.02, 'take_profit_multiple': 2.0,
        'total_profit': 0, 'num_trades': 0,
        'long_profit': 0, 'short_profit': 0,
        'num_long_trades': 0, 'num_short_trades': 0
    }

    # Use new compatibility function to find result file
    filename = find_best_result_file(crypto_id, param_set)

    loaded_json = None
    if filename:
        try:
            with open(filename, 'r') as f:
                raw_json = json.load(f)
            
            # Normalize the data to old format for compatibility
            loaded_json = normalize_result_data(raw_json, filename)
            
            if loaded_json and loaded_json.get('best_params'):
                logging.info(f"Loaded backtest results from {filename}")
                
                best_overall_params = loaded_json['best_params']
                best_overall_win_rate = loaded_json['results'].get('win_rate', 0.0)
                df_for_charting = df.copy()
                best_config_name = f"{DEFAULT_TIMEFRAME}_{DEFAULT_INTERVAL}"
                best_strategy_name = loaded_json.get('strategy_name', 'Unknown')
                latest_backtest_timestamp = os.path.getmtime(filename)
                
                # Ensure required parameters exist
                for param, default_value in default_params.items():
                    if param not in best_overall_params:
                        best_overall_params[param] = default_value
                        
                logging.info(f"Strategy: {best_strategy_name}")
                logging.info(f"Total Profit/Loss: {loaded_json['results']['total_profit_loss']:.2f}")
                logging.info(f"Win Rate: {best_overall_win_rate:.2f}%")
            else:
                logging.error(f"Invalid or empty result file: {filename}")
                
        except Exception as e:
            logging.error(f"Error loading result file {filename}: {e}")
    else:
        logging.error(f"No backtest results found for {crypto_id}. Using default parameters.")

    # Prepare all_backtest_results for the single loaded result
    if loaded_json:
        all_backtest_results = {
            best_config_name: {
                'result_data': loaded_json,
                'df': df.copy()
            }
        }
    else:
        # Use defaults if no results found
        best_overall_params = default_params
        best_strategy_name = 'EMA_Only'
        all_backtest_results = {}

    logging.info("\n--- All Backtest Results ---")
    for config_name, results_dict in all_backtest_results.items():
        result_data = results_dict.get('result_data')
        if not result_data or not result_data.get('best_params'):
            logging.info(f"  {config_name}: No backtest file found or file is empty.")
            continue

        strategy_name = result_data.get('strategy_name', 'Unknown')
        results = result_data['best_params']
        
        logging.info(f"  {config_name} (Strategy: {strategy_name})")
        if result_data.get('results', {}).get('total_profit_loss', 0) <= 0:
            logging.info(f"    No profitable parameters found.")
        else:
            logging.info(f"    Total Profit={result_data.get('results', {}).get('total_profit_loss', 0):.2f}, Total Trades={result_data.get('results', {}).get('total_trades', 0)}")
            logging.info(f"    Longs:  {result_data.get('results', {}).get('num_long_trades', 0)} trades, Profit: {result_data.get('results', {}).get('long_profit', 0):.2f}")
            logging.info(f"    Shorts: {result_data.get('results', {}).get('num_short_trades', 0)} trades, Profit: {result_data.get('results', {}).get('short_profit', 0):.2f}")
            logging.info(f"    Params: Short SMA({results.get('short_sma_period')}), Long SMA({results.get('long_sma_period')}), " \
                          f"RSI OB({results.get('rsi_overbought')}), RSI OS({results.get('rsi_oversold')}), " \
                          f"MACD Fast({results.get('macd_fast_period')}), MACD Slow({results.get('macd_slow_period')}), MACD Signal({results.get('macd_signal_period')})")

    if not best_overall_params or (loaded_json and loaded_json.get('results', {}).get('total_profit_loss', 0) <= 0):
        logging.info("\nNo profitable strategy found in any backtest. Using default parameters.")
        if not best_overall_params:
            best_overall_params = default_params
            best_strategy_name = 'EMA_Only'

    logging.info("\n--- Applying Best Overall Parameters for Charting ---")

    df['short_sma'] = calculate_sma(df, best_overall_params.get('short_sma_period', 20))
    df['long_sma'] = calculate_sma(df, best_overall_params.get('long_sma_period', 50))
    df['rsi'] = calculate_rsi(df)
    df = df.join(calculate_macd(df, best_overall_params.get('macd_fast_period', 12), best_overall_params.get('macd_slow_period', 26), best_overall_params.get('macd_signal_period', 9)))
    
    optimal_percentage_change = auto_discover_percentage_change(df, df.index[0])
    if optimal_percentage_change is None:
        logging.warning("Optimal percentage change could not be determined. Using default.")
        optimal_percentage_change = 0.005

    first_timestamp = df.index[0]
    swing_highs_df, swing_lows_df = find_swing_points(df, percentage_change=optimal_percentage_change, min_bars_confirmation=2)
    resistance_lines = find_support_resistance_lines(swing_highs_df, 'resistance', first_timestamp)
    support_lines = find_support_resistance_lines(swing_lows_df, 'support', first_timestamp)

    latest_price_point = df.iloc[-1]
    latest_relative_timestamp = (latest_price_point.name.timestamp() - first_timestamp.timestamp())

    active_resistance, active_support = None, None
    resistance_lines_sorted = sorted(resistance_lines, key=lambda x: x['intercept'], reverse=True)
    support_lines_sorted = sorted(support_lines, key=lambda x: x['intercept'])

    min_diff_resistance = float('inf')
    for r_line in resistance_lines_sorted:
        r_y_at_latest_time = r_line['slope'] * latest_relative_timestamp + r_line['intercept']
        if r_y_at_latest_time >= latest_price_point['price']:
            diff = r_y_at_latest_time - latest_price_point['price']
            if diff < min_diff_resistance:
                min_diff_resistance = diff
                active_resistance = r_line

    min_diff_support = float('inf')
    for s_line in support_lines_sorted:
        s_y_at_latest_time = s_line['slope'] * latest_relative_timestamp + s_line['intercept']
        if s_y_at_latest_time <= latest_price_point['price']:
            diff = latest_price_point['price'] - s_y_at_latest_time
            if diff < min_diff_support:
                min_diff_support = diff
                active_support = s_line

    logging.info("\n--- Trade Signals and Backtest Simulation ---")
    initial_capital = 100.0
    trade_size_percentage = 1.0 # 100% of current capital per trade

    for config_name, results_dict in all_backtest_results.items():
        result_data = results_dict.get('result_data')
        logging.info(f"\n--- Results for {config_name} ---")

        if not result_data or not result_data.get('best_params') or result_data.get('results', {}).get('total_profit_loss', 0) <= 0:
            strategy_name = result_data.get('strategy_name', 'N/A') if result_data else 'N/A'
            logging.info(f"No profitable strategy found for this timeframe (last run with '{strategy_name}'). Skipping simulation.")
            continue

        strategy_name = result_data.get('strategy_name', 'Unknown')
        best_params_for_config = result_data['best_params']
        
        logging.info(f"  Strategy: {strategy_name}")
        logging.info(f"  Initial Capital: {initial_capital:.2f}") # This initial_capital is for the display, not from the backtest result
        logging.info(f"  Final Capital: {initial_capital + result_data.get('results', {}).get('total_profit_loss', 0.0):.2f}")
        logging.info(f"  Total Profit/Loss: {result_data.get('results', {}).get('total_profit_loss', 0.0):.2f}")
        logging.info(f"  Total Trades: {result_data.get('results', {}).get('total_trades', 0)}")
        logging.info(f"  Winning Trades: {result_data.get('results', {}).get('winning_trades', 0)}")
        logging.info(f"  Losing Trades: {result_data.get('results', {}).get('losing_trades', 0)}")
        logging.info(f"  Win Rate: {result_data.get('results', {}).get('win_rate', 0.0):.2f}%")

        # Get current signal for the latest data point (optional, but good for real-time context)
        # Load strategy config dynamically
        strategy_config = load_strategy_config(strategy_name)
        current_df = results_dict['df']
        latest_signal_df = current_df.iloc[-1:] # Get only the last row for signal generation
        current_signal = get_trade_signal(latest_signal_df, strategy_config, best_params_for_config)
        logging.info(f"  Current Signal (latest data point): {current_signal}")

    # Load strategy config for the best strategy
    best_strategy_config = load_strategy_config(best_strategy_name)

    return df_for_charting, resistance_lines, support_lines, active_resistance, active_support, crypto_id, best_config_name, all_backtest_results, best_overall_params, best_strategy_config, best_strategy_name, best_overall_win_rate

def main():
    pd.set_option('display.float_format', '{:f}'.format)
    parser = argparse.ArgumentParser(description='Crypto Pricer App')
    parser.add_argument('--crypto', type=str, default='bitcoin', help='Cryptocurrency ID')
    parser.add_argument('--param-set', type=str, required=True, help='The parameter set to use for loading backtest results (e.g., "tiny", "1d_5m").')
    parser.add_argument('--interval', type=int, default=60, help='Interval in seconds for the monitoring loop. 0 to run once.')
    parser.add_argument('--intermediate-stop-loss', type=float, default=0.1, help='Intermediate stop loss percentage.')
    args = parser.parse_args()

    if args.interval == 0:
        chart_data = run_analysis(args.crypto, args.param_set, for_live_trading=False)
        # Force chart generation even if no profitable strategy is found
        if chart_data is None: # If run_analysis returned None, we need to fetch data again for charting
            logging.info("No profitable strategy found, but attempting to generate chart of raw data.")
            # Re-fetch data for charting purposes
            max_duration_seconds = max(pd.Timedelta(c['duration']).total_seconds() for c in backtest_configs.values())
            days_to_fetch = math.ceil(max_duration_seconds / (24 * 3600))
            ohlc_data = get_crypto_data(args.crypto, days_to_fetch)
            if not ohlc_data:
                logging.error(f"Could not fetch data for {args.crypto}. Cannot generate chart.")
                return

            df_for_charting = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'price'])
            df_for_charting['timestamp'] = pd.to_datetime(df_for_charting['timestamp'], unit='ms')
            df_for_charting.set_index('timestamp', inplace=True)

            # Provide dummy values for other chart_data components
            resistance_lines = []
            support_lines = []
            active_resistance = None
            active_support = None
            crypto_id = args.crypto
            best_config_name = "raw_data"
            chart_strategy_name = "raw_data"
            # Dummy values for backtest results and params
            all_backtest_results = {}
            best_overall_params = {}
            best_strategy_config = {}
            best_strategy_name = "raw_data"
            best_overall_win_rate = 0.0

        if chart_data: # If run_analysis returned data, use it
            df_for_charting, resistance_lines, support_lines, active_resistance, active_support, crypto_id, best_config_name, all_backtest_results, best_overall_params, best_strategy_config, best_strategy_name, best_overall_win_rate = chart_data
            chart_strategy_name = all_backtest_results.get(best_config_name, {}).get('result_data', {}).get('strategy_name', 'default')
        
        start_date = df_for_charting.index[0].strftime('%Y-%m-%d')
        end_date = df_for_charting.index[-1].strftime('%Y-%m-%d')
        chart_freq_str = pd.infer_freq(df_for_charting.index)
        filename = f"{crypto_id}_{start_date}_to_{end_date}_{chart_strategy_name}_{chart_freq_str}_chart.png"
        generate_chart(df_for_charting, resistance_lines, support_lines, active_resistance, active_support, crypto_id, filename)
    else:
        logging.info("\n--- Starting Live Trading Simulation ---")
        # First, run analysis once to determine the best strategy and parameters
        chart_data = run_analysis(args.crypto, args.param_set, for_live_trading=True)
        if not chart_data:
            logging.error("Could not determine a profitable strategy for live simulation. Exiting.")
            return

        df_for_charting, resistance_lines, support_lines, active_resistance, active_support, crypto_id, best_config_name, all_backtest_results, best_overall_params, best_strategy_config, best_strategy_name, best_overall_win_rate = chart_data

        if not best_overall_params or not best_strategy_config:
            logging.error("No profitable strategy found to initiate live trading. Exiting.")
            return

        logging.info(f"Initiating live simulation with best strategy: {best_strategy_name}")
        
        initial_capital_live = 100.0
        
        # Calculate hybrid position size based on volatility and recent performance
        recent_trades = []  # Initialize empty for first calculation
        trade_size_percentage_live = calculate_hybrid_position_size(args.crypto, 1.0, recent_trades)
        
        # Log position sizing decision
        daily_vol = get_daily_volatility(args.crypto)
        logging.info(f"Daily volatility for {args.crypto}: {daily_vol:.1%}")
        logging.info(f"Using hybrid position sizing: {trade_size_percentage_live:.1%}")
        if daily_vol > 0.20:
            logging.info("  → High volatility detected: Using fixed aggressive sizing (95%)")
        else:
            logging.info("  → Low volatility detected: Using dynamic performance-based sizing")
        
        start_time_live = datetime.now() # Capture start time

        live_trader = LiveTrader(
            crypto_id=args.crypto,
            initial_capital=initial_capital_live,
            trade_size_percentage=trade_size_percentage_live,
            strategy_config=best_strategy_config,
            params=best_overall_params,
            simulation_start_time=start_time_live, # Pass start time to LiveTrader
            win_rate=best_overall_win_rate, # Pass win rate to LiveTrader
            spread_percentage=best_overall_params.get('spread_percentage', 0.01),
            slippage_percentage=best_overall_params.get('slippage_percentage', 0.0005),
            intermediate_stop_loss_percentage=args.intermediate_stop_loss,
            best_config_name=best_config_name # Pass best_config_name
        )

        try:
            while True:
                if not live_trader.execute_trade_step():
                    break # Exit loop if monitoring was refused or data fetch failed
                logging.info(f"\nWaiting for {args.interval} seconds before the next run...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logging.info("\nLive monitoring stopped by user.")
            live_trader.save_results()  # save_results() doesn't take parameters

if __name__ == "__main__":
    main()
