import logging
import time
import threading
from datetime import datetime, timedelta, time as dt_time
from decimal import Decimal
from typing import List, Dict, Any
import pandas as pd
import uuid # Import uuid for generating unique IDs

from core.app_config import Config
from core.data_fetcher import get_crypto_data_merged, get_current_prices
from pricer_compatibility_fix import find_best_result_file
from strategy import Strategy
from indicators import Indicators
from config import strategy_configs
import json
import os
from core.crypto_discovery import CryptoDiscovery
from core.trading_engine import TradingEngine
from core.optimizer import CoinGeckoRateLimitError
from core.result_manager import ResultManager # Import ResultManager

from core.scheduler import get_scheduler

class PaperTradingEngine:
    _instance = None

    def __new__(cls, config: Config = None):
        if cls._instance is None:
            if config is None:
                raise ValueError("Config must be provided for the first instantiation of PaperTradingEngine.")
            cls._instance = super(PaperTradingEngine, cls).__new__(cls)
            cls._instance._initialized = False # Use a flag to prevent re-initialization
        return cls._instance

    def __init__(self, config: Config):
        if self._initialized:
            return
        self._initialized = True

        self.config = config
        self.total_capital = config.PAPER_TRADING_TOTAL_CAPITAL
        self.capital_per_trade = config.PAPER_TRADING_MIN_POSITION_VALUE
        self.max_concurrent_positions = int(self.total_capital / self.capital_per_trade)
        
        self.open_positions = []
        self.trade_history = []
        self.portfolio_value = self.total_capital
        self.analysis_history = []
        self.current_analysis_state: Dict[str, Any] = {}
        self.last_analysis_run_time: Optional[datetime] = None
        
        # Ensure results directory exists
        os.makedirs(self.config.RESULTS_DIR, exist_ok=True)
        self.trades_log_path = os.path.join(self.config.RESULTS_DIR, 'paper_trades.json')
        self.analysis_history_path = os.path.join(self.config.RESULTS_DIR, 'paper_analysis_history.json')

        # Load existing analysis history if available
        if os.path.exists(self.analysis_history_path):
            try:
                with open(self.analysis_history_path, 'r') as f:
                    self.analysis_history = json.load(f)
                logging.info(f"Loaded {len(self.analysis_history)} entries into analysis history from {self.analysis_history_path}")
            except Exception as e:
                logging.error(f"Failed to load analysis history from {self.analysis_history_path}: {e}")

        # Load existing trades if available
        if os.path.exists(self.trades_log_path):
            try:
                with open(self.trades_log_path, 'r') as f:
                    trades_data = json.load(f)
                    self.open_positions = trades_data.get('open_positions', [])
                    self.trade_history = trades_data.get('trade_history', [])
                    self.portfolio_value = trades_data.get('portfolio_value', self.total_capital)
                logging.info(f"Loaded {len(self.open_positions)} open positions and {len(self.trade_history)} trade history entries from {self.trades_log_path}")
            except Exception as e:
                logging.error(f"Failed to load trades from {self.trades_log_path}: {e}")

        self.crypto_discovery = CryptoDiscovery(cache_dir=self.config.CACHE_DIR)
        self.trading_engine = TradingEngine(config=self.config) # Instantiate TradingEngine

        logging.info("--- Paper Trading Engine Initialized ---")
        logging.info(f"Total Capital: ${self.total_capital:.2f}")
        logging.info(f"Capital per Trade: ${self.capital_per_trade:.2f}")
        logging.info(f"Max Concurrent Positions: {self.max_concurrent_positions}")

    def check_optimization_status(self):
        """
        Checks if optimization results are available for the monitored cryptos.
        """
        volatile_cryptos = self._get_volatile_cryptos()
        if not volatile_cryptos:
            return {
                "status": "no_volatile_cryptos",
                "message": "No volatile cryptocurrencies found."
            }

        total_volatile_cryptos = len(volatile_cryptos)
        cryptos_with_optimization_files = 0
        cryptos_with_profitable_strategies = 0

        available_strategies = self.trading_engine.get_strategies()
        for crypto_id in volatile_cryptos:
            has_optimization_file_for_crypto = False
            has_profitable_strategy_for_crypto = False

            for strategy_info in available_strategies:
                strategy_name = strategy_info['name']
                filename = f"best_params_{crypto_id}_{strategy_name}.json"
                filepath = os.path.join(self.config.RESULTS_DIR, filename)

                if os.path.exists(filepath):
                    has_optimization_file_for_crypto = True
                    optimization_result = self.trading_engine.get_optimization_results(crypto_id, strategy_name)
                    if optimization_result and optimization_result.get('best_params'):
                        profit = optimization_result.get('backtest_result', {}).get('total_profit_percentage', 0)
                        if profit > 0:
                            has_profitable_strategy_for_crypto = True
                            break # Found a profitable strategy for this crypto, move to next crypto

            if has_optimization_file_for_crypto:
                cryptos_with_optimization_files += 1
            if has_profitable_strategy_for_crypto:
                cryptos_with_profitable_strategies += 1

        if cryptos_with_profitable_strategies > 0:
            return {
                "status": "found",
                "message": f"Optimization results found for {cryptos_with_profitable_strategies} out of {total_volatile_cryptos} volatile cryptocurrencies with profitable strategies."
            }
        elif cryptos_with_optimization_files == total_volatile_cryptos and cryptos_with_profitable_strategies == 0:
            return {
                "status": "no_profitable_strategies",
                "message": f"Optimization results found for all {total_volatile_cryptos} volatile cryptos, but none are profitable. Please run the optimizer again."
            }
        elif cryptos_with_optimization_files > 0 and cryptos_with_profitable_strategies < total_volatile_cryptos:
            return {
                "status": "some_optimized_some_not",
                "message": f"Optimization results found for {cryptos_with_optimization_files} out of {total_volatile_cryptos} volatile cryptos, but not all. Please run the optimizer again."
            }
        else: # This covers the case where cryptos_with_optimization_files is 0
            return {
                "status": "not_found",
                "message": "No optimization results found for any of the volatile cryptocurrencies. Please run the optimizer."
            }

    

    def stop(self):
        logging.info("Stopping paper trading engine...")
        scheduler = get_scheduler()
        scheduler.remove_job('analysis_task')
        scheduler.remove_job('price_monitoring_task')
        logging.info("Paper trading engine stopped.")

    def is_running(self):
        scheduler = get_scheduler()
        analysis_job = scheduler.get_job('analysis_task')
        monitoring_job = scheduler.get_job('price_monitoring_task')
        return analysis_job is not None and monitoring_job is not None

    def get_current_analysis_state(self) -> List[Dict[str, Any]]:
        """Returns the latest analysis state for all monitored cryptos."""
        return list(self.current_analysis_state.values())

    def execute_trade(self, crypto_id, signal, params, prices):
        # Check if there's an open position for this crypto
        open_position = next((p for p in self.open_positions if p['crypto_id'] == crypto_id), None)

        if signal == "LONG":
            if not open_position:
                # Check if enough capital is available
                if self.portfolio_value >= self.capital_per_trade:
                    self._open_position(crypto_id, signal, params, prices)
                else:
                    logging.info(f"Insufficient capital to open LONG position for {crypto_id}. Capital: ${self.portfolio_value:.2f}")
            else:
                logging.info(f"Already have an open position for {crypto_id}. Not opening another LONG.")
        elif signal == "SHORT":
            if not open_position:
                # Check if enough capital is available
                if self.portfolio_value >= self.capital_per_trade:
                    self._open_position(crypto_id, signal, params, prices)
                else:
                    logging.info(f"Insufficient capital to open SHORT position for {crypto_id}. Capital: ${self.portfolio_value:.2f}")
            else:
                logging.info(f"Already have an open position for {crypto_id}. Not opening another SHORT.")
        elif signal == "EXIT_LONG":
            if open_position and open_position['signal'] == "LONG":
                current_price = prices.get(crypto_id)
                if current_price:
                    self._close_position(open_position, current_price, "exit-signal")
                else:
                    logging.warning(f"Could not fetch current price for {crypto_id} to close LONG position on exit signal.")
            else:
                logging.info(f"No active LONG position for {crypto_id} to exit.")
        elif signal == "EXIT_SHORT":
            if open_position and open_position['signal'] == "SHORT":
                current_price = prices.get(crypto_id)
                if current_price:
                    self._close_position(open_position, current_price, "exit-signal")
                else:
                    logging.warning(f"Could not fetch current price for {crypto_id} to close SHORT position on exit signal.")
            else:
                logging.info(f"No active SHORT position for {crypto_id} to exit.")
        else:
            logging.info(f"No trade executed for {crypto_id}. Signal: {signal}")

    def _is_trading_hours(self) -> bool:
        if not self.config.PAPER_TRADING_ENFORCE_TRADING_HOURS:
            return True
        now = datetime.now().time()
        start_time = dt_time(7, 0, 0)  # 7 AM
        end_time = dt_time(23, 0, 0)  # 11 PM
        return start_time <= now <= end_time

    def _get_volatile_cryptos(self):
        # Use the crypto_discovery module to get volatile cryptos
        volatile_cryptos_data = self.crypto_discovery.get_volatile_cryptos(limit=10, cache_hours=1)
        # Extract just the IDs (symbols) for now
        return [crypto['id'] for crypto in volatile_cryptos_data]

    def _close_all_positions(self):
        logging.info("--- Closing all open positions at 7 PM ---")
        positions_to_close = self.open_positions[:]
        if not positions_to_close:
            return
        
        crypto_ids_to_fetch = [p['crypto_id'] for p in positions_to_close]
        prices = get_current_prices(crypto_ids_to_fetch, self.config)

        for position in positions_to_close:
            current_price = prices.get(position['crypto_id'])
            if current_price:
                self._close_position(position, current_price, "end-of-day-close")
            else:
                logging.warning(f"Could not fetch current price for {position['crypto_id']} to close position at end of day.")
        logging.info("All open positions closed.")

    

    def _get_profitable_strategies_for_crypto(self, crypto_id: str) -> List[Strategy]:
        profitable_strategies = []
        available_strategies = self.trading_engine.get_strategies()
        result_manager = ResultManager(self.config)

        def get_timestamp_from_result(result_dict: Dict[str, Any]) -> datetime:
            timestamp_str = result_dict.get('timestamp')
            if not timestamp_str and result_dict.get('backtest_result'):
                timestamp_str = result_dict['backtest_result'].get('timestamp')
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str)
            return datetime.min # Return a very old date if no timestamp is found

        for strategy_info in available_strategies:
            strategy_name = strategy_info['name']
            
            # Use the ResultManager to get the most recent backtest, whether from optimization or manual run
            backtest_history = result_manager.get_backtest_history(crypto_id, strategy_name, limit=1)
            optimization_history = result_manager.get_optimization_history(crypto_id, strategy_name, limit=1)

            latest_result = None
            if backtest_history and optimization_history:
                if get_timestamp_from_result(backtest_history[0]) > get_timestamp_from_result(optimization_history[0]):
                    latest_result = backtest_history[0]
                else:
                    latest_result = optimization_history[0]
            elif backtest_history:
                latest_result = backtest_history[0]
            elif optimization_history:
                latest_result = optimization_history[0]

            if latest_result:
                backtest_result = latest_result.get('backtest_result', latest_result)
                profit = backtest_result.get('total_profit_percentage', 0)

                if profit > 0:
                    # In optimization results, parameters are at the top level
                    params = latest_result.get('best_params') or backtest_result.get('parameters')

                    if not params:
                        logging.warning(f"No parameters found for profitable strategy {strategy_name} for {crypto_id}. Skipping.")
                        continue

                    logging.info(f"Found profitable strategy for {crypto_id}: {strategy_name} with profit {profit:.2f}%")
                    strategy_config = strategy_configs[strategy_name]
                    indicators = Indicators()
                    strategy_config['name'] = strategy_name
                    strategy_instance = Strategy(indicators, strategy_config)
                    strategy_instance.set_params(params)
                    profitable_strategies.append(strategy_instance)
        
        if not profitable_strategies:
            logging.warning(f"No profitable strategies found for {crypto_id}.")

        return profitable_strategies

    def _get_trade_signal_for_latest(self, df: pd.DataFrame, strategy: Strategy, open_position_signal: str = None):
        try:
            long_entry, short_entry, long_exit, short_exit = strategy.generate_signals(df, strategy.params)

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

    def _get_aggregated_trade_signal(self, df: pd.DataFrame, profitable_strategies: List[Strategy], open_position_signal: str = None):
        if not profitable_strategies:
            return "HOLD"

        buy_signals = 0
        sell_signals = 0
        exit_long_signals = 0
        exit_short_signals = 0
        
        for strategy in profitable_strategies:
            signal = self._get_trade_signal_for_latest(df, strategy, open_position_signal)
            if signal == "LONG":
                buy_signals += 1
            elif signal == "SHORT":
                sell_signals += 1
            elif signal == "EXIT_LONG":
                exit_long_signals += 1
            elif signal == "EXIT_SHORT":
                exit_short_signals += 1
        
        num_strategies = len(profitable_strategies)
        majority_threshold = num_strategies / 2

        # Prioritize exit signals
        if open_position_signal == "LONG" and exit_long_signals > majority_threshold:
            return "EXIT_LONG"
        elif open_position_signal == "SHORT" and exit_short_signals > majority_threshold:
            return "EXIT_SHORT"
        
        # Then check entry signals
        if buy_signals > 0: # Any profitable strategy says buy
            return "LONG"
        elif sell_signals > 0: # Any profitable strategy says sell
            return "SHORT"
        
        return "HOLD"

    def analysis_task(self):
        if not self._is_trading_hours():
            logging.debug("Skipping analysis task: outside trading hours.")
            return

        logging.info("--- Running Analysis Task ---")
        self.last_analysis_run_time = datetime.now().isoformat()
        
        volatile_cryptos = self._get_volatile_cryptos()
        logging.info(f"Found {len(volatile_cryptos)} volatile cryptos: {volatile_cryptos}")

        # Convert volatile_cryptos to a set for efficient lookup
        volatile_crypto_ids = {crypto_id for crypto_id in volatile_cryptos}

        # Reconcile open positions and monitored cryptos with the latest volatile list
        cryptos_to_remove_from_monitoring = []
        for crypto_id in list(self.current_analysis_state.keys()): # Iterate over a copy of keys
            if crypto_id not in volatile_crypto_ids:
                cryptos_to_remove_from_monitoring.append(crypto_id)

        for crypto_id in cryptos_to_remove_from_monitoring:
            logging.info(f"Crypto {crypto_id} is no longer volatile. Stopping monitoring and closing positions.")
            # Close any open positions for this crypto
            positions_to_close = [p for p in self.open_positions if p['crypto_id'] == crypto_id]
            if positions_to_close:
                # Fetch current price to close position
                prices = get_current_prices([crypto_id], self.config)
                current_price = prices.get(crypto_id)
                if current_price:
                    for position in positions_to_close:
                        self._close_position(position, current_price, "no-longer-volatile")
                else:
                    logging.warning(f"Could not fetch current price for {crypto_id} to close position as it's no longer volatile.")
            
            # Remove from current analysis state
            if crypto_id in self.current_analysis_state:
                del self.current_analysis_state[crypto_id]
            logging.info(f"Stopped monitoring {crypto_id}.")

        # Batch fetch prices for all volatile cryptos
        prices = get_current_prices(volatile_cryptos, self.config)
        
        for crypto_id in volatile_cryptos:
            open_position = next((p for p in self.open_positions if p['crypto_id'] == crypto_id), None)

            # If max concurrent positions reached and no open position for this crypto, skip
            if not open_position and len(self.open_positions) >= self.max_concurrent_positions:
                logging.info(f"Max concurrent positions reached. Skipping new analysis for {crypto_id}.")
                continue

            # Get profitable strategies for the crypto
            profitable_strategies = self._get_profitable_strategies_for_crypto(crypto_id)
            current_price = prices.get(crypto_id)

            if not profitable_strategies:
                logging.info(f"No profitable strategies found for {crypto_id}. Skipping.")
                continue

            logging.info(f"Found {len(profitable_strategies)} profitable strategies for {crypto_id}.")

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

            # Get aggregated signal
            open_position_signal_type = open_position['signal'] if open_position else None
            signal = self._get_aggregated_trade_signal(df, profitable_strategies, open_position_signal=open_position_signal_type)

            logging.info(f"Aggregated Signal for {crypto_id}: {signal}")

            if not current_price:
                logging.warning(f"Could not fetch current price for {crypto_id} during analysis task. Skipping analysis history save.")
                continue

            # Get the backtest result from the first profitable strategy, if available
            backtest_result = None
            strategy_used = "N/A"
            if profitable_strategies:
                # Assuming the first profitable strategy is representative
                strategy_used = profitable_strategies[0].config.get('name', 'N/A')
                optimization_result = self.trading_engine.get_optimization_results(crypto_id, strategy_used)
                if optimization_result and optimization_result.get('backtest_result'):
                    backtest_result = optimization_result['backtest_result']

            analysis_entry = {
                'analysis_id': str(uuid.uuid4()),
                'crypto_id': crypto_id,
                'strategy_used': strategy_used,
                'current_signal': signal,
                'current_price': current_price,
                'analysis_timestamp': datetime.now().isoformat(),
                'active_resistance_lines': [], # Placeholder for now
                'active_support_lines': [],    # Placeholder for now
                'parameters_used': representative_params if 'representative_params' in locals() else {},
                'timeframe_days': 1, # Based on get_crypto_data_merged(days=1)
                'engine_version': "1.0.0-paper-trader", # Placeholder
                'backtest_result': backtest_result
            }
            self.current_analysis_state[crypto_id] = analysis_entry # Update current state

            # Limit the size of the analysis history
            self.analysis_history.append(analysis_entry) # Still append to history for logging/storage
            self.analysis_history = self.analysis_history[-100:]
            self._save_analysis_history()

            # Execute trade based on signal
            if signal != "HOLD":
                # For execution, we need params. Since we are using multiple strategies,
                # we can use the params of the first profitable strategy as a representative,
                # or refine this to be an average/median of params if applicable.
                # For now, let's use the params of the first profitable strategy.
                representative_params = profitable_strategies[0].params
                self.execute_trade(crypto_id, signal, representative_params, prices)

    def _open_position(self, crypto_id, signal, params, prices):
        current_price = prices.get(crypto_id)
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
        if not self._is_trading_hours():
            logging.debug("Skipping price monitoring task: outside trading hours.")
            return

        if not self.open_positions:
            return

        logging.info("--- Running Price Monitoring Task ---")
        
        crypto_ids_to_monitor = [p['crypto_id'] for p in self.open_positions]
        prices = get_current_prices(crypto_ids_to_monitor, self.config)

        for position in self.open_positions[:]: # Iterate over a copy
            current_price = prices.get(position['crypto_id'])
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

    def _save_analysis_history(self):
        try:
            analysis_history_path = os.path.join(self.config.RESULTS_DIR, 'paper_analysis_history.json')
            with open(analysis_history_path, 'w') as f:
                json.dump(self.analysis_history, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save analysis history: {e}")


def run_analysis_task(job_id):
    """Wrapper function to run the analysis task as a job."""
    from core.logger_config import setup_job_logging
    log_path = setup_job_logging(job_id)
    logger = logging.getLogger(job_id)
    logger.info(f"Starting analysis task job (id: {job_id})... Log file: {log_path}")

    try:
        engine = PaperTradingEngine(config=Config())
        engine.analysis_task()
        logger.info("Analysis task job finished.")
    except Exception as e:
        logger.error(f"An error occurred during the analysis task job: {e}", exc_info=True)


def run_price_monitoring_task(job_id):
    """Wrapper function to run the price monitoring task as a job."""
    from core.logger_config import setup_job_logging
    log_path = setup_job_logging(job_id)
    logger = logging.getLogger(job_id)
    logger.info(f"Starting price monitoring task job (id: {job_id})... Log file: {log_path}")

    try:
        engine = PaperTradingEngine(config=Config())
        engine.price_monitoring_task()
        logger.info("Price monitoring task job finished.")
    except Exception as e:
        logger.error(f"An error occurred during the price monitoring task job: {e}", exc_info=True)
