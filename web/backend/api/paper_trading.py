from flask import Blueprint, jsonify
from flask_restful import Resource, Api
import logging

# Add project root to path to allow importing core modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from auth.middleware import requires_auth
from core.data_fetcher import get_current_prices

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
            prices = get_current_prices(crypto_ids, self.paper_trading_engine.config)

            for pos in open_positions:
                current_price = prices.get(pos['crypto_id'])
                if current_price:
                    current_value = current_price * pos['size_crypto']
                    pnl_usd = (current_price - pos['entry_price']) * pos['size_crypto'] if pos['signal'] == 'LONG' else (pos['entry_price'] - current_price) * pos['size_crypto']
                else:
                    current_value = pos['size_usd'] # Fallback to entry value
                    pnl_usd = 0

                position_data = {
                    **pos,
                    'current_price': current_price,
                    'current_value_usd': current_value,
                    'pnl_usd': pnl_usd
                }
                open_positions_with_current_value.append(position_data)

            status = {
                'is_running': self.paper_trading_engine.is_running(),
                'monitored_cryptos': self.paper_trading_engine._get_volatile_cryptos(),
                'open_positions': open_positions_with_current_value,
                'portfolio_value': self.paper_trading_engine.portfolio_value or 0,
                'trade_history': self.paper_trading_engine.trade_history,
                'max_concurrent_positions': self.paper_trading_engine.max_concurrent_positions,
                'capital_per_trade': self.paper_trading_engine.capital_per_trade,
                'initial_capital': self.paper_trading_engine.total_capital,
                'analysis_history': self.paper_trading_engine.get_current_analysis_state(),
                'optimization_status': self.paper_trading_engine.check_optimization_status()
            }
            return jsonify(status)
        except Exception as e:
            self.logger.error(f"Error getting paper trading status: {e}")
            if "'Strategy' object has no attribute 'set_params'" in str(e):
                return jsonify({'error': 'No analysis data available. Please run the optimizer.'}), 500
            return jsonify({'error': 'Failed to get paper trading status'}), 500