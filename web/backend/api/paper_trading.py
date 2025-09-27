from flask import jsonify, current_app
from flask_restful import Resource, Api
import logging
import json # Added json import

# Add project root to path to allow importing core modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from auth.middleware import requires_auth


# This will be imported from the main app file
# from app import paper_trading_engine

class PaperTradingAPI(Resource):
    def __init__(self, **kwargs):
        self.paper_trading_engine = kwargs['engine']
        self.logger = logging.getLogger(__name__)

    @requires_auth('read:paper_trading')
    def get(self):
        """Returns the current status of the paper trading engine."""
        try:
            open_positions_with_current_value = []
            open_positions = self.paper_trading_engine.open_positions
            crypto_ids = [pos['crypto_id'] for pos in open_positions]
            
            # Use the data_fetcher from the paper_trading_engine
            if self.paper_trading_engine.data_fetcher is None:
                self.logger.error("DataFetcher not initialized in PaperTradingEngine.")
                return {'error': 'DataFetcher not available'}, 500
            prices = self.paper_trading_engine.data_fetcher.get_current_prices(crypto_ids)

            for pos in open_positions:
                current_price = prices.get(pos['crypto_id'])
                if current_price:
                    # Calculate PnL for the open position
                    if pos['signal'] == 'LONG':
                        pnl_usd = (current_price - pos['entry_price']) * pos['size_crypto']
                        current_value_for_portfolio = current_price * pos['size_crypto'] # For long, current value is market value
                    else: # SHORT
                        pnl_usd = (pos['entry_price'] - current_price) * pos['size_crypto']
                        # For short, the "value" contributing to portfolio is initial capital + PnL
                        current_value_for_portfolio = pos['size_usd'] + pnl_usd
                else:
                    # Fallback if current price is not available
                    pnl_usd = 0
                    current_value_for_portfolio = pos['size_usd'] # Assume no change from initial capital

                position_data = {
                    **pos,
                    'current_price': current_price,
                    'current_value_usd': current_value_for_portfolio, # This will be used for portfolio sum
                    'pnl_usd': pnl_usd,
                    'cost_usd': pos['size_usd']
                }
                open_positions_with_current_value.append(position_data)

            invested_capital = sum(pos['size_usd'] for pos in open_positions)
            current_positions_value = sum(pos['current_value_usd'] for pos in open_positions_with_current_value)
            initial_capital = self.paper_trading_engine.total_capital
            
            real_time_portfolio_value = self.paper_trading_engine.available_capital + current_positions_value

            logging.root.info(f"Last analysis run time from engine: {self.paper_trading_engine.last_analysis_run_time}")
            status = {
                'is_running': self.paper_trading_engine.is_running(),
                'monitored_cryptos': self.paper_trading_engine._get_volatile_cryptos(),
                'open_positions': open_positions_with_current_value,
                'portfolio_value': real_time_portfolio_value,
                'available_capital': self.paper_trading_engine.available_capital,
                'trade_history': self.paper_trading_engine.trade_history,
                'max_concurrent_positions': self.paper_trading_engine.max_concurrent_positions,
                'capital_per_trade': self.paper_trading_engine.capital_per_trade,
                'initial_capital': self.paper_trading_engine.total_capital,
                'analysis_history': self.paper_trading_engine.get_current_analysis_state(),
                'optimization_status': self.paper_trading_engine.check_optimization_status(),
                'last_analysis_run': self.paper_trading_engine.last_analysis_run_time
            }
            return status
        except Exception as e:
            logging.root.error(f"Error getting paper trading status: {e}")
            if "'Strategy' object has no attribute 'set_params'" in str(e):
                return {'error': 'No analysis data available. Please run the optimizer.'}, 500
            return {'error': 'Failed to get paper trading status'}, 500

class TradeHistoryAPI(Resource):
    def __init__(self, **kwargs):
        self.logger = logging.getLogger(__name__)

    @requires_auth('read:paper_trading_history') # Assuming a new permission for history
    def get(self, date: str, symbol: str):
        """Returns the trade history for a given date and symbol."""
        try:
            log_dir = os.path.join("data", "trade_history")
            filename = os.path.join(log_dir, f"{date}_{symbol.replace('/', '-')}.json")

            if not os.path.exists(filename):
                return {"message": "Trade history not found for this date and symbol."}, 404

            trades = []
            with open(filename, "r") as f:
                for line in f:
                    try:
                        trades.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Error decoding JSON from trade history file {filename}: {e}")
                        continue
            return jsonify(trades)
        except Exception as e:
            self.logger.error(f"Error retrieving trade history for {symbol} on {date}: {e}")
            return {"error": "Failed to retrieve trade history."}, 500