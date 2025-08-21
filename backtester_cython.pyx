# distutils: extra_compile_args=-fopenmp
# distutils: extra_link_args=-fopenmp

import numpy as np
cimport numpy as np
from libc.math cimport fmax, fmin, fabs

# Define data types for Cython
ctypedef np.float64_t DTYPE_t
ctypedef np.uint8_t UBYTE_t

cdef void update_recent_trades(double* recent_trades, int* count, double new_trade):
    """Update the recent trades array with a new trade result."""
    cdef int i
    
    if count[0] < 5:
        recent_trades[count[0]] = new_trade
        count[0] += 1
    else:
        # Shift array left and add new trade at the end
        for i in range(4):
            recent_trades[i] = recent_trades[i + 1]
        recent_trades[4] = new_trade

cdef double calculate_position_size(double* recent_trades, int count, 
                                  double base_size, double min_size, double max_size):
    """Calculate dynamic position size based on recent performance."""
    cdef int wins = 0
    cdef int i
    cdef double multiplier = 1.0
    cdef double avg_profit = 0.0
    cdef double total_profit = 0.0
    
    if count < 2:
        return base_size
    
    # Calculate average profit of recent trades
    for i in range(max(0, count - 3), count):
        total_profit += recent_trades[i]
    
    if count >= 3:
        avg_profit = total_profit / 3.0
    else:
        avg_profit = total_profit / count
    
    # Count wins in recent trades
    for i in range(max(0, count - 3), count):
        if recent_trades[i] > 0:
            wins += 1
    
    # More aggressive position sizing
    if avg_profit > 5.0:  # Strong recent performance
        multiplier = 2.0  # Double position size
    elif wins >= 2 and count >= 3:  # 2+ wins out of 3
        multiplier = 1.8  # Increase size by 80%
    elif wins == 1 and count >= 3:  # 1 win out of 3
        multiplier = 1.0  # Keep normal size
    elif wins == 0 and count >= 3:  # 0 wins out of 3
        multiplier = 0.3  # Significantly reduce size
    else:
        multiplier = 1.0  # Default
    
    # Apply multiplier and enforce limits
    cdef double new_size = base_size * multiplier
    return fmax(min_size, fmin(max_size, new_size))

def run_backtest_cython(np.ndarray[DTYPE_t, ndim=1] prices,
                        np.ndarray[UBYTE_t, ndim=1] long_entry,
                        np.ndarray[UBYTE_t, ndim=1] short_entry,
                        np.ndarray[UBYTE_t, ndim=1] long_exit,
                        np.ndarray[UBYTE_t, ndim=1] short_exit,
                        np.ndarray[DTYPE_t, ndim=1] atr_values,
                        double atr_multiple,
                        double fixed_stop_loss_percentage,
                        double take_profit_multiple,
                        double initial_capital,
                        double spread_percentage,
                        double slippage_percentage,
                        double daily_volatility=0.0):  # New parameter for volatility

    cdef int n = prices.shape[0]
    cdef double current_capital = initial_capital
    cdef int position = 0  # 0: None, 1: Long, -1: Short
    cdef double entry_price = 0.0
    cdef double highest_price_since_entry = 0.0
    cdef double lowest_price_since_entry = 0.0
    cdef double trailing_stop_loss = 0.0
    cdef double position_size = 0.0
    cdef double fixed_stop_loss_price = 0.0
    cdef double take_profit_price = 0.0

    cdef int total_trades = 0
    cdef int winning_trades = 0
    cdef int losing_trades = 0
    cdef double total_profit_loss = 0.0
    cdef double long_profit = 0.0
    cdef double short_profit = 0.0
    cdef int num_long_trades = 0
    cdef int num_short_trades = 0

    # Position sizing variables
    cdef double base_position_percentage = 0.20  # 20% base position size for dynamic
    cdef double fixed_position_percentage = 0.95  # 95% for high volatility
    cdef double volatility_threshold = 0.20  # 20% daily move threshold
    cdef double min_position_percentage = 0.05   # 5% minimum
    cdef double max_position_percentage = 0.95   # 95% maximum
    cdef double recent_trades[5]  # Track last 5 trades
    cdef int recent_trades_count = 0
    cdef double current_position_percentage = base_position_percentage
    cdef int use_fixed_sizing = 0  # Flag for sizing method
    
    # Determine sizing method based on volatility
    if fabs(daily_volatility) > volatility_threshold:
        use_fixed_sizing = 1

    cdef double current_price, current_ask_price, current_bid_price
    cdef double profit_loss, exit_price, risk_amount

    for i from 0 <= i < n:
        current_price = prices[i]
        current_ask_price = current_price * (1 + spread_percentage)
        current_bid_price = current_price * (1 - spread_percentage)

        # Update trailing stop loss for open positions
        if position == 1: # Long position
            highest_price_since_entry = fmax(highest_price_since_entry, current_price)
            if atr_values[i] > 0:
                trailing_stop_loss = highest_price_since_entry - (atr_values[i] * atr_multiple)
            if current_price <= trailing_stop_loss and trailing_stop_loss > 0:
                long_exit[i] = 1 # Force exit

        elif position == -1: # Short position
            lowest_price_since_entry = fmin(lowest_price_since_entry, current_price)
            if atr_values[i] > 0:
                trailing_stop_loss = lowest_price_since_entry + (atr_values[i] * atr_multiple)
            if current_price >= trailing_stop_loss and trailing_stop_loss > 0:
                short_exit[i] = 1 # Force exit

        # Check fixed stop loss and take profit for open positions
        if position == 1: # Long position
            if current_price <= fixed_stop_loss_price and fixed_stop_loss_price > 0:
                long_exit[i] = 1 # Force exit due to stop loss
            elif current_price >= take_profit_price and take_profit_price > 0:
                long_exit[i] = 1 # Force exit due to take profit
        elif position == -1: # Short position
            if current_price >= fixed_stop_loss_price and fixed_stop_loss_price > 0:
                short_exit[i] = 1 # Force exit due to stop loss
            elif current_price <= take_profit_price and take_profit_price > 0:
                short_exit[i] = 1 # Force exit due to take profit

        if position == 0: # No open position
            if long_entry[i]:
                position = 1
                # Apply spread and slippage correctly - don't double apply
                entry_price = current_price * (1 + spread_percentage + slippage_percentage)
                total_trades += 1
                
                # Choose position sizing method based on volatility
                if use_fixed_sizing:
                    # High volatility: use fixed aggressive sizing
                    position_size = current_capital * fixed_position_percentage
                else:
                    # Low volatility: use dynamic sizing based on recent performance
                    current_position_percentage = calculate_position_size(recent_trades, recent_trades_count, 
                                                                       base_position_percentage, 
                                                                       min_position_percentage, 
                                                                       max_position_percentage)
                    position_size = current_capital * current_position_percentage

                # Calculate fixed stop loss and take profit for LONG
                fixed_stop_loss_price = entry_price * (1 - fixed_stop_loss_percentage)
                risk_amount = entry_price - fixed_stop_loss_price
                take_profit_price = entry_price + (risk_amount * take_profit_multiple)

                highest_price_since_entry = current_price
                if atr_values[i] > 0:
                    trailing_stop_loss = highest_price_since_entry - (atr_values[i] * atr_multiple)

            elif short_entry[i]:
                position = -1
                # Apply spread and slippage correctly - don't double apply
                entry_price = current_price * (1 - spread_percentage - slippage_percentage)
                total_trades += 1
                
                # Choose position sizing method based on volatility
                if use_fixed_sizing:
                    # High volatility: use fixed aggressive sizing
                    position_size = current_capital * fixed_position_percentage
                else:
                    # Low volatility: use dynamic sizing based on recent performance
                    current_position_percentage = calculate_position_size(recent_trades, recent_trades_count, 
                                                                       base_position_percentage, 
                                                                       min_position_percentage, 
                                                                       max_position_percentage)
                    position_size = current_capital * current_position_percentage

                # Calculate fixed stop loss and take profit for SHORT
                fixed_stop_loss_price = entry_price * (1 + fixed_stop_loss_percentage)
                risk_amount = fixed_stop_loss_price - entry_price
                take_profit_price = entry_price - (risk_amount * take_profit_multiple)

                lowest_price_since_entry = current_price
                if atr_values[i] > 0:
                    trailing_stop_loss = lowest_price_since_entry + (atr_values[i] * atr_multiple)

        elif position == 1: # Long position
            if long_exit[i] or i == n - 1:
                # Apply spread and slippage correctly - don't double apply
                exit_price = current_price * (1 - spread_percentage - slippage_percentage)
                profit_loss = (exit_price - entry_price) / entry_price * position_size
                current_capital += profit_loss

                total_profit_loss += profit_loss
                long_profit += profit_loss
                num_long_trades += 1

                # Update recent trades history (only for dynamic sizing)
                if not use_fixed_sizing:
                    update_recent_trades(recent_trades, &recent_trades_count, profit_loss)

                if profit_loss > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                position = 0
                position_size = 0.0
                highest_price_since_entry = 0.0
                trailing_stop_loss = 0.0
                fixed_stop_loss_price = 0.0
                take_profit_price = 0.0

        elif position == -1: # Short position
            if short_exit[i] or i == n - 1:
                # Apply spread and slippage correctly - don't double apply
                exit_price = current_price * (1 + spread_percentage + slippage_percentage)
                profit_loss = (entry_price - exit_price) / entry_price * position_size
                current_capital += profit_loss

                total_profit_loss += profit_loss
                short_profit += profit_loss
                num_short_trades += 1

                # Update recent trades history (only for dynamic sizing)
                if not use_fixed_sizing:
                    update_recent_trades(recent_trades, &recent_trades_count, profit_loss)

                if profit_loss > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                position = 0
                position_size = 0.0
                lowest_price_since_entry = 0.0
                trailing_stop_loss = 0.0
                fixed_stop_loss_price = 0.0
                take_profit_price = 0.0

    cdef double win_rate = 0.0
    if total_trades > 0:
        win_rate = <double>winning_trades / total_trades

    return {
        "final_capital": current_capital,
        "total_profit_loss": total_profit_loss,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "long_profit": long_profit,
        "short_profit": short_profit,
        "num_long_trades": num_long_trades,
        "num_short_trades": num_short_trades
    }