import logging
import time
import schedule
import threading
from datetime import datetime
import pandas as pd

from core.app_config import Config
from core.data_fetcher import get_crypto_data_merged, get_current_price
from pricer_compatibility_fix import find_best_result_file
from strategy import Strategy
from indicators import Indicators
from config import strategy_configs
import json
import os
from core.crypto_discovery import CryptoDiscovery
from core.trading_engine import TradingEngine
from core.optimizer import CoinGeckoRateLimitError # Add this import # Add this import

class PaperTradingEngine:
    def __init__(self, config: Config):
        self.config = config
        self.total_capital = config.PAPER_TRADING_TOTAL_CAPITAL
        self.capital_per_trade = config.PAPER_TRADING_MIN_POSITION_VALUE
        self.max_concurrent_positions = int(self.total_capital / self.capital_per_trade)
        
        self.open_positions = []
        self.trade_history = []
        self.portfolio_value = self.total_capital
        
        # Ensure results directory exists
        os.makedirs(self.config.RESULTS_DIR, exist_ok=True)
        self.trades_log_path = os.path.join(self.config.RESULTS_DIR, 'paper_trades.json')

        self._running = False
        self._engine_thread = None
        self.crypto_discovery = CryptoDiscovery(cache_dir=self.config.CACHE_DIR)
        self.trading_engine = TradingEngine(config=self.config) # Instantiate TradingEngine

        logging.info("--- Paper Trading Engine Initialized ---")
        logging.info(f"Total Capital: ${self.total_capital:.2f}")
        logging.info(f"Capital per Trade: ${self.capital_per_trade:.2f}")
        logging.info(f"Max Concurrent Positions: {self.max_concurrent_positions}")

    def start(self):
        if self._running:
            logging.info("Paper trading engine is already running.")
            return

        self._running = True
        self._engine_thread = threading.Thread(target=self._run_scheduled_tasks, daemon=True)
        self._engine_thread.start()
        logging.info("Paper trading engine started.")

    def stop(self):
        if not self._running:
            logging.info("Paper trading engine is not running.")
            return

        logging.info("Stopping paper trading engine...")
        self._running = False
        if self._engine_thread and self._engine_thread.is_alive():
            self._engine_thread.join(timeout=5) # Wait for the thread to finish
            if self._engine_thread.is_alive():
                logging.warning("Paper trading engine thread did not terminate gracefully.")
        logging.info("Paper trading engine stopped.")

    def is_running(self):
        return self._running

    def execute_trade(self, crypto_id, signal, params):
        # Check if there's an open position for this crypto
        open_position = next((p for p in self.open_positions if p['crypto_id'] == crypto_id), None)

        if signal == "LONG":
            if not open_position:
                # Check if enough capital is available
                if self.portfolio_value >= self.capital_per_trade:
                    self._open_position(crypto_id, signal, params)
                else:
                    logging.info(f"Insufficient capital to open LONG position for {crypto_id}. Capital: ${self.portfolio_value:.2f}")
            else:
                logging.info(f"Already have an open position for {crypto_id}. Not opening another LONG.")
        elif signal == "SHORT":
            if not open_position:
                # Check if enough capital is available
                if self.portfolio_value >= self.capital_per_trade:
                    self._open_position(crypto_id, signal, params)
                else:
                    logging.info(f"Insufficient capital to open SHORT position for {crypto_id}. Capital: ${self.portfolio_value:.2f}")
            else:
                logging.info(f"Already have an open position for {crypto_id}. Not opening another SHORT.")
        elif signal == "EXIT_LONG":
            if open_position and open_position['signal'] == "LONG":
                current_price = get_current_price(crypto_id)
                if current_price:
                    self._close_position(open_position, current_price, "exit-signal")
                else:
                    logging.warning(f"Could not fetch current price for {crypto_id} to close LONG position on exit signal.")
            else:
                logging.info(f"No active LONG position for {crypto_id} to exit.")
        elif signal == "EXIT_SHORT":
            if open_position and open_position['signal'] == "SHORT":
                current_price = get_current_price(crypto_id)
                if current_price:
                    self._close_position(open_position, current_price, "exit-signal")
                else:
                    logging.warning(f"Could not fetch current price for {crypto_id} to close SHORT position on exit signal.")
            else:
                logging.info(f"No active SHORT position for {crypto_id} to exit.")
        else:
            logging.info(f"No trade executed for {crypto_id}. Signal: {signal}")

    def _run_scheduled_tasks(self):
        logging.info("Paper trading scheduled tasks runner started.")
        # Run analysis task once at the beginning
        self.analysis_task()

        # Schedule tasks
        schedule.every(self.config.PAPER_TRADING_ANALYSIS_INTERVAL_MINUTES).minutes.do(self.analysis_task)
        schedule.every(self.config.PAPER_TRADING_MONITORING_INTERVAL_SECONDS).seconds.do(self.price_monitoring_task)

        while self._running:
            schedule.run_pending()
            time.sleep(1)
        logging.info("Paper trading scheduled tasks runner stopped.")

    def _get_volatile_cryptos(self):
        # Use the crypto_discovery module to get volatile cryptos
        volatile_cryptos_data = self.crypto_discovery.get_volatile_cryptos()
        # Extract just the IDs (symbols) for now
        return [crypto['id'] for crypto in volatile_cryptos_data]

    def _get_best_strategy_and_params(self, crypto_id):
        best_strategy_name = None
        best_params = None
        highest_profit = -float('inf')

        available_strategies = self.trading_engine.get_strategies()
        
        for strategy_info in available_strategies:
            strategy_name = strategy_info['name']
            
            # Get the full optimization result to check profit
            optimization_result = self.trading_engine.get_optimization_results(crypto_id, strategy_name)
            
            if optimization_result and optimization_result.get('best_params'):
                profit = optimization_result.get('backtest_result', {}).get('total_profit_percentage', 0)
                
                if profit > highest_profit:
                    highest_profit = profit
                    best_strategy_name = strategy_name
                    best_params = optimization_result['best_params']
        
        if best_strategy_name and best_params:
            logging.info(f"Found best optimized strategy for {crypto_id}: {best_strategy_name} with profit {highest_profit:.2f}%")
            return best_strategy_name, best_params
        
        logging.warning(f"No best optimized strategy found for {crypto_id}. Skipping.")
        return None, None

    def _get_trade_signal_for_latest(self, df: pd.DataFrame, strategy: Strategy, params: dict, open_position_signal: str = None):
        try:
            long_entry, short_entry, long_exit, short_exit = strategy.generate_signals(df, params)

            # Prioritize exit signals
            if open_position_signal == "LONG" and not long_exit.empty and long_exit.iloc[-1]:
                return "EXIT_LONG"
            elif open_position_signal == "SHORT" and not short_exit.empty and short_exit.iloc[-1]:
                return "EXIT_SHORT"

            # Then check entry signals
            if not long_entry.empty and long_entry.iloc[-1]:
                return "LONG"
            elif not short_entry.empty and short_entry.iloc[-1]:
                return "SHORT"
            else:
                return "HOLD"
        except Exception as e:
            logging.error(f"Error generating trade signal: {e}")
            return "HOLD"

    def analysis_task(self):
        logging.info("--- Running Analysis Task ---")
        
        volatile_cryptos = self._get_volatile_cryptos()
        
        for crypto_id in volatile_cryptos:
            open_position = next((p for p in self.open_positions if p['crypto_id'] == crypto_id), None)

            # If max concurrent positions reached and no open position for this crypto, skip
            if not open_position and len(self.open_positions) >= self.max_concurrent_positions:
                logging.info(f"Max concurrent positions reached. Skipping new analysis for {crypto_id}.")
                continue

            strategy_name, params = self._get_best_strategy_and_params(crypto_id)
            if not strategy_name or not params:
                continue

            # Fetch data (1 day of minute-level data)
            try:
                df = get_crypto_data_merged(crypto_id, days=1, config=self.config)
            except CoinGeckoRateLimitError as e:
                logging.warning(f"Rate limit hit for {crypto_id}: {e}. Skipping this crypto for now.")
                continue
            if df is None or df.empty:
                logging.error(f"No data for {crypto_id}. Skipping.")
                continue

            time.sleep(self.config.DATA_FETCH_DELAY_SECONDS)

            # Get signal
            strategy_config = strategy_configs[strategy_name]
            indicators = Indicators()
            strategy = Strategy(indicators, strategy_config)
            
            # Pass open_position_signal if there's an open position
            open_position_signal_type = open_position['signal'] if open_position else None
            signal = self._get_trade_signal_for_latest(df, strategy, params, open_position_signal=open_position_signal_type)

            logging.info(f"Signal for {crypto_id}: {signal}")

            # Execute trade based on signal
            if signal != "HOLD":
                self.execute_trade(crypto_id, signal, params)

    def _open_position(self, crypto_id, signal, params):
        current_price = get_current_price(crypto_id)
        if not current_price:
            logging.error(f"Could not fetch current price for {crypto_id} to open position.")
            return

        # Use _place_order to simulate the buy
        position = self._place_order(crypto_id, "BUY", signal, current_price, params=params)
        if position:
            self.open_positions.append(position)
            self.portfolio_value -= position['size_usd'] # Deduct capital used for the position
            logging.info(f"Opened new {signal} position for {crypto_id} at ${current_price:.2f}. Stop loss at ${position['stop_loss_price']:.2f}. Capital remaining: ${self.portfolio_value:.2f}")
            self._save_trades()


    def price_monitoring_task(self):
        if not self.open_positions:
            return

        logging.info("--- Running Price Monitoring Task ---")
        
        for position in self.open_positions[:]: # Iterate over a copy
            current_price = get_current_price(position['crypto_id'])
            if not current_price:
                logging.warning(f"Could not fetch price for {position['crypto_id']} during monitoring.")
                continue

            logging.info(f"Monitoring {position['crypto_id']}: Current Price=${current_price:.2f}, SL=${position['stop_loss_price']:.2f}")

            stop_loss_triggered = False
            if position['signal'] == 'LONG' and current_price <= position['stop_loss_price']:
                stop_loss_triggered = True
            elif position['signal'] == 'SHORT' and current_price >= position['stop_loss_price']:
                stop_loss_triggered = True

            if stop_loss_triggered:
                self._close_position(position, current_price, "stop-loss")

    def _close_position(self, position, exit_price, reason):
        # Use _place_order to simulate the close
        closed_trade = self._place_order(position['crypto_id'], "CLOSE", reason, exit_price, position_to_close=position)
        
        if closed_trade:
            self.portfolio_value += closed_trade['size_usd'] + closed_trade['pnl_usd'] # Return capital used + PnL
            
            self.trade_history.append(closed_trade)
            self.open_positions.remove(position)

            logging.info(f"Closed {position['signal']} position for {position['crypto_id']} at ${exit_price:.2f} due to {reason}. PnL: ${closed_trade['pnl_usd']:.2f}. New Portfolio Value: ${self.portfolio_value:.2f}")
            self._save_trades()

    def _place_order(self, crypto_id, order_type, signal, current_price, params=None, position_to_close=None):
        if order_type == "BUY": # Opening a LONG position
            if self.portfolio_value < self.capital_per_trade:
                logging.warning(f"Cannot place BUY order for {crypto_id}: Insufficient capital.")
                return None
            
            position_size_usd = self.capital_per_trade
            position_size_crypto = position_size_usd / current_price
            stop_loss_percentage = params.get('fixed_stop_loss_percentage', 0.02)
            stop_loss_price = current_price * (1 - stop_loss_percentage)

            position = {
                "crypto_id": crypto_id,
                "signal": signal,
                "entry_price": current_price,
                "stop_loss_price": stop_loss_price,
                "size_usd": position_size_usd,
                "size_crypto": position_size_crypto,
                "timestamp": datetime.now().isoformat(),
                "status": "open"
            }
            logging.info(f"Simulated BUY order for {crypto_id} at ${current_price:.2f}")
            return position

        elif order_type == "SELL": # Opening a SHORT position
            if self.portfolio_value < self.capital_per_trade:
                logging.warning(f"Cannot place SELL order for {crypto_id}: Insufficient capital.")
                return None

            position_size_usd = self.capital_per_trade
            position_size_crypto = position_size_usd / current_price
            stop_loss_percentage = params.get('fixed_stop_loss_percentage', 0.02)
            stop_loss_price = current_price * (1 + stop_loss_percentage)

            position = {
                "crypto_id": crypto_id,
                "signal": signal,
                "entry_price": current_price,
                "stop_loss_price": stop_loss_price,
                "size_usd": position_size_usd,
                "size_crypto": position_size_crypto,
                "timestamp": datetime.now().isoformat(),
                "status": "open"
            }
            logging.info(f"Simulated SELL order for {crypto_id} at ${current_price:.2f}")
            return position

        elif order_type == "CLOSE" and position_to_close: # Closing an existing position
            pnl_usd = 0
            if position_to_close['signal'] == 'LONG':
                pnl_usd = (current_price - position_to_close['entry_price']) * position_to_close['size_crypto']
            else: # SHORT
                pnl_usd = (position_to_close['entry_price'] - current_price) * position_to_close['size_crypto']
            
            closed_trade = {
                **position_to_close,
                "exit_price": current_price,
                "exit_timestamp": datetime.now().isoformat(),
                "pnl_usd": pnl_usd,
                "reason": signal, # signal here is the reason for closing (e.g., "exit-signal", "stop-loss")
                "status": "closed"
            }
            logging.info(f"Simulated CLOSE order for {crypto_id} at ${current_price:.2f}")
            return closed_trade
        
        return None

    def _save_trades(self):
        try:
            all_trades = {
                "open_positions": self.open_positions,
                "trade_history": self.trade_history,
                "portfolio_value": self.portfolio_value
            }
            with open(self.trades_log_path, 'w') as f:
                json.dump(all_trades, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save trades log: {e}")

    def run(self):
        logging.info("Starting paper trading engine...")
        
        # Run analysis task once at the beginning
        self.analysis_task()

        # Schedule tasks
        schedule.every(self.config.PAPER_TRADING_ANALYSIS_INTERVAL_MINUTES).minutes.do(self.analysis_task)
        schedule.every(self.config.PAPER_TRADING_MONITORING_INTERVAL_SECONDS).seconds.do(self.price_monitoring_task)

        while self._running:
            schedule.run_pending()
            time.sleep(1)
        logging.info("Paper trading scheduled tasks runner stopped.")

def run_paper_trader():
    config = Config()
    setup_logging(config)
    logger = logging.getLogger(__name__)

    engine = PaperTradingEngine(config)
    
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received. Stopping paper trading engine...")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        engine.start()
        logger.info("Paper trading engine started. Press Ctrl+C to stop.")
        # Keep the main thread alive while the engine thread runs
        while engine.is_running():
            time.sleep(1)
    except Exception as e:
        logger.error(f"An error occurred in the main paper trading process: {e}")
    finally:
        engine.stop()
        logger.info("Paper trading engine stopped.")