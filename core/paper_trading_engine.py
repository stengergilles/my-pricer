import logging
import time
import threading
from datetime import datetime, timedelta, time as dt_time
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import uuid # Import uuid for generating unique IDs

from core.app_config import Config
from core.data_fetcher import DataFetcher # New import
from core.rate_limiter import RateLimiter, get_shared_rate_limiter

from pricer_compatibility_fix import find_best_result_file
from strategy import Strategy
from indicators import Indicators, calculate_adx
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

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PaperTradingEngine, cls).__new__(cls)
            cls._instance._initialized = False # Use a flag to prevent re-initialization
        return cls._instance

    def __init__(self, config: Config, data_fetcher: DataFetcher = None, trading_engine: TradingEngine = None, socketio: Any = None):
        if self._initialized:
            return
        self._initialized = True
        self.logger = logging.getLogger(__name__) # Initialize logger here

        self.config = config
        self.logger.debug(f"PaperTradingEngine init: received data_fetcher is {type(data_fetcher)}") # Add this line
        self.data_fetcher = data_fetcher # Store data_fetcher
        self.socketio = socketio # Store socketio
        
        # If data_fetcher is not provided, create a default one using the global coingecko_rate_limiter
        if self.data_fetcher is None:
            from core.rate_limiter_process import start_rate_limiter_process
            import multiprocessing
            request_queue = multiprocessing.Queue()
            response_queue = multiprocessing.Queue()
            rate_limiter_process = multiprocessing.Process(
                target=start_rate_limiter_process,
                args=(request_queue, response_queue, self.config),
                daemon=True
            )
            rate_limiter_process.start()
            self.rate_limiter_process = rate_limiter_process # Store the process
            self.data_fetcher = DataFetcher(request_queue, response_queue, config)

        self.total_capital = config.PAPER_TRADING_TOTAL_CAPITAL
        self.capital_per_trade = config.PAPER_TRADING_MIN_POSITION_VALUE
        self.max_concurrent_positions = int(self.total_capital / self.capital_per_trade)
        
        self.open_positions = []
        self.trade_history = []
        self.available_capital = self.total_capital
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
                    self.available_capital = trades_data.get('available_capital', trades_data.get('portfolio_value', self.total_capital))
                logging.info(f"Loaded {len(self.open_positions)} open positions and {len(self.trade_history)} trade history entries from {self.trades_log_path}")
            except Exception as e:
                logging.error(f"Failed to load trades from {self.trades_log_path}: {e}")

        self.crypto_discovery = CryptoDiscovery(cache_dir=self.config.CACHE_DIR, data_fetcher=self.data_fetcher) # Pass data_fetcher
        self.trading_engine = trading_engine # Use the passed trading_engine

        logging.info("--- Paper Trading Engine Initialized ---")
        logging.info(f"Total Capital: ${self.total_capital:.2f}")
        logging.info(f"Capital per Trade: ${self.capital_per_trade:.2f}")
        logging.info(f"Max Concurrent Positions: {self.max_concurrent_positions}")

    def _log_trade(self, trade_data: Dict):
        """Logs trade data to a daily file for the specific crypto."""
        try:
            # Correctly construct the absolute path for the log directory
            log_dir = os.path.join(self.config.BASE_DIR, "web", "backend", "data", "trade_history")
            os.makedirs(log_dir, exist_ok=True)
            
            today_str = datetime.now().strftime("%Y-%m-%d")
            symbol = trade_data.get("symbol", "UNKNOWN").replace("/", "-")
            filename = os.path.join(log_dir, f"{today_str}_{symbol}.json")

            # Append trade data to the file
            with open(filename, "a") as f:
                f.write(json.dumps(trade_data) + "\n")
            self.logger.debug(f"Logged trade for {symbol} to {filename}")
            if self.socketio:
                self.socketio.emit('trade_update', trade_data)
        except Exception as e:
            self.logger.error(f"Error logging trade: {e}")

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
                        profit = (optimization_result.get('backtest_result') or {}).get('total_profit_percentage', 0)
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

    def execute_trade(self, crypto_id, signal, params, prices, backtest_result=None, entry_reason=None, atr_value=None):
        self.logger.info(f"Executing trade for {crypto_id} with signal {signal}")
        # Check if there's an open position for this crypto
        open_position = next((p for p in self.open_positions if p['crypto_id'] == crypto_id), None)

        if signal == "LONG":
            if not open_position:
                # Check if enough capital is available
                if self.available_capital >= self.capital_per_trade:
                    self.logger.info(f"Opening LONG position for {crypto_id}")
                    self._open_position(crypto_id, signal, params, prices, backtest_result=backtest_result, entry_reason=entry_reason, atr_value=atr_value)
                else:
                    logging.info(f"Insufficient capital to open LONG position for {crypto_id}. Capital: ${self.available_capital:.2f}")
            else:
                logging.info(f"Already have an open position for {crypto_id}. Not opening another LONG.")
        elif signal == "SHORT":
            if not open_position:
                # Check if enough capital is available
                if self.available_capital >= self.capital_per_trade:
                    self.logger.info(f"Opening SHORT position for {crypto_id}")
                    self._open_position(crypto_id, signal, params, prices, backtest_result=backtest_result, entry_reason=entry_reason, atr_value=atr_value)
                else:
                    logging.info(f"Insufficient capital to open SHORT position for {crypto_id}. Capital: ${self.available_capital:.2f}")
            else:
                logging.info(f"Already have an open position for {crypto_id}. Not opening another SHORT.")
        elif signal == "EXIT_LONG":
            if open_position and open_position['signal'] == "LONG":
                current_price = prices.get(crypto_id)
                if current_price:
                    self.logger.info(f"Closing LONG position for {crypto_id}")
                    self._close_position(open_position, current_price, entry_reason)
                else:
                    logging.warning(f"Could not fetch current price for {crypto_id} to close LONG position on exit signal.")
            else:
                logging.info(f"No active LONG position for {crypto_id} to exit.")
        elif signal == "EXIT_SHORT":
            if open_position and open_position['signal'] == "SHORT":
                current_price = prices.get(crypto_id)
                if current_price:
                    self.logger.info(f"Closing SHORT position for {crypto_id}")
                    self._close_position(open_position, current_price, entry_reason)
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
        
        if self.data_fetcher is None:
            logging.error("DataFetcher not initialized. Cannot close positions.")
            return

        crypto_ids_to_fetch = [p['crypto_id'] for p in positions_to_close]
        prices = self.data_fetcher.get_current_prices(crypto_ids_to_fetch)

        for position in positions_to_close:
            current_price = prices.get(position['crypto_id'])
            if current_price:
                self._close_position(position, current_price, "end-of-day-close")
            else:
                logging.warning(f"Could not fetch current price for {position['crypto_id']} to close position at end of day.")
        logging.info("All open positions closed.")

    

    def _get_best_profitable_strategy(self, crypto_id: str) -> Optional[Strategy]:
        profitable_strategies = []
        available_strategies = self.trading_engine.get_strategies()
        result_manager = ResultManager(self.config)

        def get_timestamp_from_result(result_dict: Dict[str, Any]) -> datetime:
            timestamp_str = result_dict.get('timestamp')
            if not timestamp_str and result_dict.get('backtest_result'):
                timestamp_str = result_dict['backtest_result'].get('timestamp')
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str)
            return datetime.min

        for strategy_info in available_strategies:
            strategy_name = strategy_info['name']
            
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
                profit = backtest_result.get('total_profit_percentage', 0) if backtest_result else 0

                min_profit_threshold = (self.config.PAPER_TRADING_SPREAD_PERCENTAGE + self.config.PAPER_TRADING_SLIPPAGE_PERCENTAGE) * 100 + self.config.PAPER_TRADING_MIN_PROFIT_BUFFER
                if profit > min_profit_threshold:
                    params = latest_result.get('best_params') or backtest_result.get('parameters')
                    if not params:
                        logging.warning(f"No parameters found for profitable strategy {strategy_name} for {crypto_id}. Skipping.")
                        continue

                    strategy_config = strategy_configs[strategy_name]
                    indicators = Indicators()
                    strategy_config['name'] = strategy_name
                    strategy_instance = Strategy(indicators, strategy_config)
                    strategy_instance.set_params(params)
                    strategy_instance.backtest_trend = backtest_result.get('backtest_trend')
                    strategy_instance.profit = profit # Store profit for sorting
                    profitable_strategies.append(strategy_instance)
        
        if not profitable_strategies:
            logging.warning(f"No profitable strategies found for {crypto_id}.")
            return None

        # Sort by profit and return the best one
        best_strategy = sorted(profitable_strategies, key=lambda s: s.profit, reverse=True)[0]
        logging.info(f"Best profitable strategy for {crypto_id}: {best_strategy.config['name']} with profit {best_strategy.profit:.2f}%")
        return best_strategy

    def _get_trade_signal(self, df: pd.DataFrame, strategy: Strategy, open_position_signal: str = None) -> Tuple[str, List[str]]:
        signal = self._get_trade_signal_for_latest(df, strategy, open_position_signal)
        return signal, [strategy.config.get('name', 'N/A')] if signal != "HOLD" else []

    def _get_trade_signal_for_latest(self, df: pd.DataFrame, strategy: Strategy, open_position_signal: str = None):
        try:
            # 1. Determine current trend from the latest data
            adx_data = calculate_adx(df, window=strategy.params.get('adx_period', 14))
            current_trend = "NEUTRAL"
            if not adx_data.empty and not adx_data['pdi'].isnull().all():
                last_pdi = adx_data['pdi'].iloc[-1]
                last_ndi = adx_data['ndi'].iloc[-1]
                if last_pdi > last_ndi:
                    current_trend = "UP"
                else:
                    current_trend = "DOWN"

            self.logger.info(f"Current trend for {strategy.config.get('name')}: {current_trend}")

            # 2. Generate signals from the strategy
            long_entry, short_entry, long_exit, short_exit = strategy.generate_signals(df, strategy.params)

            # 3. Prioritize exit signals
            if open_position_signal == "LONG" and not long_exit.empty and long_exit.iloc[-1]:
                return "EXIT_LONG"
            elif open_position_signal == "SHORT" and not short_exit.empty and short_exit.iloc[-1]:
                return "EXIT_SHORT"

            # 4. Then check entry signals based on trend
            if current_trend == "UP":
                if not long_entry.empty and long_entry.iloc[-1]:
                    return "LONG"
            elif current_trend == "DOWN":
                if not short_entry.empty and short_entry.iloc[-1]:
                    return "SHORT"
            
            return "HOLD"
        except Exception as e:
            self.logger.error(f"Error generating trade signal: {e}", exc_info=True)
            return "HOLD"

    def analysis_task(self):
        if not self._is_trading_hours():
            logging.debug("Skipping analysis task: outside trading hours.")
            return

        logging.info("--- Running Analysis Task ---")
        self.last_analysis_run_time = datetime.now().isoformat()
        
        volatile_cryptos = self._get_volatile_cryptos()
        volatile_crypto_ids = set(volatile_cryptos)
        open_position_cryptos = {p['crypto_id'] for p in self.open_positions}
        
        cryptos_to_analyze = volatile_crypto_ids | open_position_cryptos
        
        logging.info(f"Found {len(volatile_cryptos)} volatile cryptos: {volatile_cryptos}")
        logging.info(f"Found {len(open_position_cryptos)} cryptos with open positions: {list(open_position_cryptos)}")
        logging.info(f"Analyzing a total of {len(cryptos_to_analyze)} unique cryptos.")

        prices = self.data_fetcher.get_current_prices(list(cryptos_to_analyze))
        
        for crypto_id in cryptos_to_analyze:
            open_position = next((p for p in self.open_positions if p['crypto_id'] == crypto_id), None)
            is_volatile = crypto_id in volatile_crypto_ids

            if not open_position and not is_volatile:
                logging.info(f"Skipping analysis for {crypto_id} as it is not volatile and has no open position.")
                continue

            if not open_position and len(self.open_positions) >= self.max_concurrent_positions:
                logging.info(f"Max concurrent positions reached. Skipping new analysis for {crypto_id}.")
                continue

            best_strategy = self._get_best_profitable_strategy(crypto_id)
            current_price = prices.get(crypto_id)

            if not best_strategy:
                logging.info(f"No profitable strategies found for {crypto_id}. Skipping.")
                continue

            try:
                df = self.data_fetcher.get_crypto_data_merged(crypto_id, days=1)
            except CoinGeckoRateLimitError as e:
                logging.warning(f"Rate limit hit for {crypto_id}: {e}. Skipping this crypto for now.")
                continue
            if df is None or df.empty:
                logging.error(f"No data for {crypto_id}. Skipping.")
                continue

            from indicators import calculate_atr
            atr_period = best_strategy.params.get('atr_period', 14)
            atr_value = calculate_atr(df, window=atr_period).iloc[-1]

            time.sleep(self.config.DATA_FETCH_DELAY_SECONDS)

            open_position_signal_type = open_position['signal'] if open_position else None
            signal, contributing_strategies = self._get_trade_signal(df, best_strategy, open_position_signal=open_position_signal_type)

            logging.info(f"Signal for {crypto_id} using {best_strategy.config['name']}: {signal}")

            if not current_price:
                logging.warning(f"Could not fetch current price for {crypto_id} during analysis task. Skipping analysis history save.")
                continue

            strategy_used = best_strategy.config.get('name', 'N/A')
            optimization_result = self.trading_engine.get_optimization_results(crypto_id, strategy_used)
            backtest_result = optimization_result.get('backtest_result') if optimization_result else None

            analysis_entry = {
                'analysis_id': str(uuid.uuid4()),
                'crypto_id': crypto_id,
                'strategy_used': strategy_used,
                'current_signal': signal,
                'current_price': current_price,
                'analysis_timestamp': datetime.now().isoformat(),
                'active_resistance_lines': [],
                'active_support_lines': [],
                'parameters_used': best_strategy.params,
                'timeframe_days': 1,
                'engine_version': "1.0.0-paper-trader",
                'backtest_result': backtest_result
            }
            self.current_analysis_state[crypto_id] = analysis_entry

            self.analysis_history.append(analysis_entry)
            self.analysis_history = self.analysis_history[-100:]
            self._save_analysis_history()

            if signal != "HOLD":
                reason = f"{signal} triggered by {', '.join(contributing_strategies)}"
                self.execute_trade(crypto_id, signal, best_strategy.params, prices, backtest_result=backtest_result, entry_reason=reason, atr_value=atr_value)

    def _open_position(self, crypto_id, signal, params, prices, backtest_result=None, entry_reason=None, atr_value=None):
        current_price = prices.get(crypto_id)
        if not current_price:
            logging.error(f"Could not fetch current price for {crypto_id} to open position.")
            return

        order_type = "BUY" if signal == "LONG" else "SELL"
        position = self._place_order(crypto_id, order_type, signal, current_price, params=params, backtest_result=backtest_result, entry_reason=entry_reason, atr_value=atr_value)
        if position:
            self.open_positions.append(position)
            self.available_capital -= position['size_usd'] # Deduct capital used for the position
            logging.info(f"Opened new {signal} position for {crypto_id} at ${current_price:.2f}. Stop loss at ${position['stop_loss_price']:.2f}. Capital remaining: ${self.available_capital:.2f}")
            
            trade_data = {
                "timestamp": datetime.now().isoformat(),
                "symbol": crypto_id,
                "trade_type": signal, # LONG or SHORT
                "price": current_price,
                "quantity": position['size_crypto'],
                "total_value": position['size_usd'],
                "balance_after": self.available_capital,
                "position_id": position.get('position_id') # Assuming position_id might be added later
            }
            self._log_trade(trade_data)
            self._save_trades()


    def price_monitoring_task(self):
        if not self._is_trading_hours():
            logging.debug("Skipping price monitoring task: outside trading hours.")
            return

        if not self.open_positions:
            return

        self.logger.info("--- Running Price Monitoring Task ---")
        
        if self.data_fetcher is None:
            logging.error("DataFetcher not initialized. Cannot monitor prices.")
            return

        crypto_ids_to_monitor = [p['crypto_id'] for p in self.open_positions]
        prices = self.data_fetcher.get_current_prices(crypto_ids_to_monitor) # Use data_fetcher

        for position in self.open_positions[:]: # Iterate over a copy
            current_price = prices.get(position['crypto_id'])
            if not current_price:
                logging.warning(f"Could not fetch price for {position['crypto_id']} during monitoring.")
                continue

            self.logger.info(f"Monitoring {position['crypto_id']} ({position['signal']}): Entry Price=${position['entry_price']:.2f}, Current Price=${current_price:.2f}, SL=${position['stop_loss_price']:.2f}")

            # Trailing stop loss logic
            if position['signal'] == 'LONG':
                if current_price > position.get('highest_price_seen', position['entry_price']):
                    position['highest_price_seen'] = current_price
                    atr_value = position.get('atr_value')
                    atr_multiple = position.get('atr_stop_loss_multiple')
                    if atr_value and atr_multiple:
                        new_stop_loss_price = current_price - (atr_value * atr_multiple)
                        if new_stop_loss_price > position['stop_loss_price']:
                            position['stop_loss_price'] = new_stop_loss_price
                            self.logger.info(f"Updated ATR-based trailing stop loss for {position['crypto_id']} to ${new_stop_loss_price:.2f}")
                    else: # Fallback to percentage if ATR values are not available
                        new_stop_loss_price = current_price * (1 - position['trailing_stop_loss_percentage'])
                        if new_stop_loss_price > position['stop_loss_price']:
                            position['stop_loss_price'] = new_stop_loss_price
                            self.logger.info(f"Updated percentage-based trailing stop loss for {position['crypto_id']} to ${new_stop_loss_price:.2f}")

            elif position['signal'] == 'SHORT':
                if current_price < position.get('lowest_price_seen', position['entry_price']):
                    position['lowest_price_seen'] = current_price
                    atr_value = position.get('atr_value')
                    atr_multiple = position.get('atr_stop_loss_multiple')
                    if atr_value and atr_multiple:
                        new_stop_loss_price = current_price + (atr_value * atr_multiple)
                        if new_stop_loss_price < position['stop_loss_price']:
                            position['stop_loss_price'] = new_stop_loss_price
                            self.logger.info(f"Updated ATR-based trailing stop loss for {position['crypto_id']} to ${new_stop_loss_price:.2f}")
                    else: # Fallback to percentage if ATR values are not available
                        new_stop_loss_price = current_price * (1 + position['trailing_stop_loss_percentage'])
                        if new_stop_loss_price < position['stop_loss_price']:
                            position['stop_loss_price'] = new_stop_loss_price
                            self.logger.info(f"Updated percentage-based trailing stop loss for {position['crypto_id']} to ${new_stop_loss_price:.2f}")

            # Take-profit logic (moved before stop-loss)
            take_profit_price = position.get("take_profit_price")
            self.logger.info(f"TP Check for {position['crypto_id']}: Current Price=${current_price:.2f}, Take Profit Price=${take_profit_price}, Signal={position['signal']}")
            if take_profit_price is not None:
                if position['signal'] == 'LONG' and current_price >= take_profit_price:
                    self.logger.info(f"Take profit triggered for LONG position on {position['crypto_id']}. Current Price: ${current_price:.2f}, TP: ${take_profit_price:.2f}")
                    self._close_position(position, current_price, "take-profit")
                    continue # Move to the next position if take-profit is hit
                elif position['signal'] == 'SHORT' and current_price <= take_profit_price:
                    self.logger.info(f"Take profit triggered for SHORT position on {position['crypto_id']}. Current Price: ${current_price:.2f}, TP: ${take_profit_price:.2f}")
                    self._close_position(position, current_price, "take-profit")
                    continue # Move to the next position if take-profit is hit

            stop_loss_triggered = False
            if position['signal'] == 'LONG' and current_price <= position['stop_loss_price']:
                self.logger.info(f"Stop loss triggered for LONG position on {position['crypto_id']}")
                stop_loss_triggered = True
            elif position['signal'] == 'SHORT' and current_price >= position['stop_loss_price']:
                self.logger.info(f"Stop loss triggered for SHORT position on {position['crypto_id']}")
                stop_loss_triggered = True

            if stop_loss_triggered:
                self._close_position(position, current_price, "stop-loss")
                continue # Move to the next position

    def _close_position(self, position, exit_price, reason):
        # Use _place_order to simulate the close
        closed_trade = self._place_order(position['crypto_id'], "CLOSE", reason, exit_price, position_to_close=position)
        
        if closed_trade:
            self.available_capital += closed_trade['size_usd'] + closed_trade['pnl_usd'] # Return capital used + PnL
            
            self.trade_history.append(closed_trade)
            self.open_positions.remove(position)

            logging.info(f"Closed {position['signal']} position for {position['crypto_id']} at ${exit_price:.2f} due to {reason}. PnL: ${closed_trade['pnl_usd']:.2f}. New Portfolio Value: ${self.available_capital:.2f}")
            
            trade_data = {
                "timestamp": datetime.now().isoformat(),
                "symbol": position['crypto_id'],
                "trade_type": f"EXIT_{position['signal']}", # EXIT_LONG or EXIT_SHORT
                "price": exit_price,
                "quantity": position['size_crypto'],
                "total_value": position['size_usd'], # Original value of the position
                "pnl_usd": closed_trade['pnl_usd'],
                "reason": reason,
                "balance_after": self.available_capital,
                "position_id": position.get('position_id')
            }
            self._log_trade(trade_data)
            self._save_trades()

    def _place_order(self, crypto_id, order_type, signal, current_price, params=None, position_to_close=None, backtest_result=None, entry_reason=None, atr_value=None):
        if order_type == "BUY": # Opening a LONG position
            if self.available_capital < self.capital_per_trade:
                logging.warning(f"Cannot place BUY order for {crypto_id}: Insufficient capital.")
                return None
            
            position_size_usd = self.capital_per_trade
            position_size_crypto = position_size_usd / current_price
            atr_stop_loss_multiple = params.get('atr_stop_loss_multiple', 2.0)
            stop_loss_price = current_price - (atr_value * atr_stop_loss_multiple)
            trailing_stop_loss_percentage = params.get('trailing_stop_loss_percentage', 0.02)
            take_profit_multiple = params.get('take_profit_multiple', 1.5) # Get take_profit_multiple
            risk_amount = current_price - stop_loss_price # Calculate risk amount
            take_profit_price = current_price + (risk_amount * take_profit_multiple) # Calculate take_profit_price

            position = {
                "crypto_id": crypto_id,
                "signal": signal,
                "entry_price": current_price,
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_price, # Store take_profit_price
                "size_usd": position_size_usd,
                "size_crypto": position_size_crypto,
                "timestamp": datetime.now().isoformat(),
                "status": "open",
                "backtest_profit_percentage": backtest_result.get('total_profit_percentage') if backtest_result else None,
                "entry_reason": entry_reason,
                "highest_price_seen": current_price,
                "trailing_stop_loss_percentage": trailing_stop_loss_percentage,
                "take_profit_multiple": take_profit_multiple, # Store take_profit_multiple
                "atr_value": atr_value,
                "atr_stop_loss_multiple": atr_stop_loss_multiple
            }
            logging.info(f"Simulated BUY order for {crypto_id} at ${current_price:.2f}")
            return position

        elif order_type == "SELL": # Opening a SHORT position
            if self.available_capital < self.capital_per_trade:
                logging.warning(f"Cannot place SELL order for {crypto_id}: Insufficient capital.")
                return None

            position_size_usd = self.capital_per_trade
            position_size_crypto = position_size_usd / current_price
            atr_stop_loss_multiple = params.get('atr_stop_loss_multiple', 2.0)
            stop_loss_price = current_price + (atr_value * atr_stop_loss_multiple)
            trailing_stop_loss_percentage = params.get('trailing_stop_loss_percentage', 0.02)
            take_profit_multiple = params.get('take_profit_multiple', 1.5) # Get take_profit_multiple
            risk_amount = stop_loss_price - current_price # Calculate risk amount for SHORT
            take_profit_price = current_price - (risk_amount * take_profit_multiple) # Calculate take_profit_price for SHORT

            position = {
                "crypto_id": crypto_id,
                "signal": signal,
                "entry_price": current_price,
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_price, # Store take_profit_price
                "size_usd": position_size_usd,
                "size_crypto": position_size_crypto,
                "timestamp": datetime.now().isoformat(),
                "status": "open",
                "backtest_profit_percentage": backtest_result.get('total_profit_percentage') if backtest_result else None,
                "entry_reason": entry_reason,
                "lowest_price_seen": current_price,
                "trailing_stop_loss_percentage": trailing_stop_loss_percentage,
                "take_profit_multiple": take_profit_multiple, # Store take_profit_multiple
                "atr_value": atr_value,
                "atr_stop_loss_multiple": atr_stop_loss_multiple
            }
            logging.info(f"Simulated SELL order for {crypto_id} at ${current_price:.2f}")
            return position

        elif order_type == "CLOSE" and position_to_close: # Closing an existing position
            pnl_usd = 0
            if position_to_close['signal'] == 'LONG':
                pnl_usd = (current_price - position_to_close['entry_price']) * position_to_close['size_crypto']
            else: # SHORT
                pnl_usd = (position_to_close['entry_price'] - current_price) * position_to_close['size_crypto']
            
            exit_timestamp = datetime.now().isoformat()
            
            exit_pnl_status = "profitable" if pnl_usd > 0 else ("unprofitable" if pnl_usd < 0 else "breakeven")

            # The 'reason' variable already holds the trigger for closing (e.g., "stop-loss", "take-profit")
            # We will use this as the exit_reason, and add exit_pnl_status for clarity.
            # No change to 'reason' itself, as per user's request to not hide the dust.
            reason_for_exit_trigger = signal

            closed_trade = {
                **position_to_close,
                "exit_price": current_price,
                "exit_timestamp": exit_timestamp,
                "pnl_usd": pnl_usd,
                "reason": reason_for_exit_trigger,
                "status": "closed",

                # Add new fields for frontend
                "entry_date": position_to_close.get('timestamp'),
                "exit_date": exit_timestamp,
                "entry_reason": position_to_close.get('entry_reason', 'N/A'),
                "exit_reason": reason_for_exit_trigger,
                "exit_pnl_status": exit_pnl_status
            }
            logging.info(f"Simulated CLOSE order for {crypto_id} at ${current_price:.2f}")
            return closed_trade
        
        return None

    def _save_trades(self):
        try:
            all_trades = {
                "open_positions": self.open_positions,
                "trade_history": self.trade_history,
                "available_capital": self.available_capital
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


def run_analysis_task(job_id, config: Config):
    """Wrapper function to run the analysis task as a job."""
    from core.logger_config import setup_job_logging
    log_path = setup_job_logging(job_id)
    logger = logging.getLogger(job_id)
    logger.info(f"Starting analysis task job (id: {job_id})... Log file: {log_path}")

    try:
        engine = PaperTradingEngine(config=config)
        engine.analysis_task()
        logger.info("Analysis task job finished.")
    except Exception as e:
        logger.error(f"An error occurred during the analysis task job: {e}", exc_info=True)


def run_price_monitoring_task(job_id, config: Config):
    """Wrapper function to run the price monitoring task as a job."""
    from core.logger_config import setup_job_logging
    log_path = setup_job_logging(job_id)
    logger = logging.getLogger(job_id)
    logger.info(f"Starting price monitoring task job (id: {job_id})... Log file: {log_path}")

    try:
        engine = PaperTradingEngine(config=config)
        engine.price_monitoring_task()
        logger.info("Price monitoring task job finished.")
    except Exception as e:
        logger.error(f"An error occurred during the price monitoring task job: {e}", exc_info=True)