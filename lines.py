import pandas as pd
from scipy.stats import linregress
from itertools import combinations

def find_swing_points(df, percentage_change=0.05, min_bars_confirmation=2):
    swing_highs = []
    swing_lows = []

    if len(df) < min_bars_confirmation + 2:
        return pd.DataFrame(swing_highs), pd.DataFrame(swing_lows)

    # Initialize with the first point
    last_swing_point = df.iloc[0]
    current_trend = None  # 'up' or 'down'

    for i in range(1, len(df)):
        current_price = df.iloc[i]

        if current_trend is None:
            # Determine initial trend
            if current_price['price'] > last_swing_point['price'] * (1 + percentage_change):
                current_trend = 'up'
            elif current_price['price'] < last_swing_point['price'] * (1 - percentage_change):
                current_trend = 'down'

        elif current_trend == 'up':
            if current_price['price'] < last_swing_point['price'] * (1 - percentage_change):
                # Potential trend reversal: check for confirmation
                confirmed = True
                for j in range(1, min_bars_confirmation + 1):
                    if (i + j) >= len(df) or df.iloc[i + j]['price'] >= current_price['price']:
                        confirmed = False
                        break
                if confirmed:
                    swing_highs.append(last_swing_point)
                    last_swing_point = current_price
                    current_trend = 'down'
            elif current_price['price'] > last_swing_point['price']:
                # Continue up trend, update last swing point if higher
                last_swing_point = current_price

        elif current_trend == 'down':
            if current_price['price'] > last_swing_point['price'] * (1 + percentage_change):
                # Potential trend reversal: check for confirmation
                confirmed = True
                for j in range(1, min_bars_confirmation + 1):
                    if (i + j) >= len(df) or df.iloc[i + j]['price'] <= current_price['price']:
                        confirmed = False
                        break
                if confirmed:
                    swing_lows.append(last_swing_point)
                    last_swing_point = current_price
                    current_trend = 'up'
            elif current_price['price'] < last_swing_point['price']:
                # Continue down trend, update last swing point if lower
                last_swing_point = current_price

    return pd.DataFrame(swing_highs).reset_index(), pd.DataFrame(swing_lows).reset_index()

def calculate_line_equation(points, first_timestamp):
    if len(points) < 2:
        return None, None, None, None

    # Convert timestamps to numerical values relative to the first_timestamp of the entire dataset
    x = [(p['timestamp'] - first_timestamp).total_seconds() for p in points]
    y = [p['price'] for p in points]

    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    return slope, intercept, r_value, std_err

def find_support_resistance_lines(swing_points_df, line_type, first_timestamp):
    lines = []
    # Consider combinations of 2 points
    for num_points in [2]:
        for combo in combinations(swing_points_df.itertuples(index=False), num_points):
            # Convert namedtuple to dictionary for calculate_line_equation
            points = [{'timestamp': p[0], 'price': p.price} for p in combo]
            slope, intercept, r_value, std_err = calculate_line_equation(points, first_timestamp)

            if slope is not None:
                lines.append({
                    'type': line_type,
                    'points': [p[0] for p in combo],
                    'equation': f"y = {slope:.6f}x + {intercept:.2f}",
                    'slope': slope,
                    'intercept': intercept,
                    'r_value': r_value,
                    'std_err': std_err
                })
    return lines

def analyze_line_durations(df, resistance_lines, support_lines, first_timestamp):
    durations = []

    # Calculate relative timestamps for the entire DataFrame once
    df['relative_timestamp'] = (df.index.map(lambda x: x.timestamp()) - first_timestamp.timestamp())

    # Sort lines by intercept to make finding closest easier
    resistance_lines = sorted(resistance_lines, key=lambda x: x['intercept'], reverse=True)
    support_lines = sorted(support_lines, key=lambda x: x['intercept'])

    current_channel = None
    channel_start_time = None

    for i in range(len(df)):
        current_price_point = df.iloc[i]
        current_price = current_price_point['price']
        current_relative_timestamp = current_price_point['relative_timestamp']

        active_resistance = None
        active_support = None

        # Find the active resistance line (closest above current price)
        for r_line in resistance_lines:
            r_y_at_current_time = r_line['slope'] * current_relative_timestamp + r_line['intercept']
            if current_price <= r_y_at_current_time:
                active_resistance = r_line
                break # Found the first resistance above

        # Find the active support line (closest below current price)
        for s_line in support_lines:
            s_y_at_current_time = s_line['slope'] * current_relative_timestamp + s_line['intercept']
            if current_price >= s_y_at_current_time:
                active_support = s_line
                break # Found the first support below

        if active_resistance and active_support:
            # Check if we are in a new channel or continuing the old one
            if current_channel is None or \
               current_channel['resistance'] != active_resistance or \
               current_channel['support'] != active_support:
                
                # If we were in a channel, record its duration
                if current_channel is not None and channel_start_time is not None:
                    duration_seconds = (current_price_point.name - channel_start_time).total_seconds()
                    if duration_seconds > 0:
                        durations.append({
                            'resistance_equation': current_channel['resistance']['equation'],
                            'support_equation': current_channel['support']['equation'],
                            'duration_seconds': duration_seconds
                        })
                
                # Start a new channel
                current_channel = {
                    'resistance': active_resistance,
                    'support': active_support
                }
                channel_start_time = current_price_point.name
        else:
            # Price is not within any clear channel, end current channel if any
            if current_channel is not None and channel_start_time is not None:
                duration_seconds = (current_price_point.name - channel_start_time).total_seconds()
                if duration_seconds > 0:
                    durations.append({
                        'resistance_equation': current_channel['resistance']['equation'],
                        'support_equation': current_channel['support']['equation'],
                        'duration_seconds': duration_seconds
                    })
            current_channel = None
            channel_start_time = None

    # Record the duration of the last channel if it was still active at the end of the data
    if current_channel is not None and channel_start_time is not None:
        duration_seconds = (df.index[-1] - channel_start_time).total_seconds()
        if duration_seconds > 0:
            durations.append({
                'resistance_equation': current_channel['resistance']['equation'],
                'support_equation': current_channel['support']['equation'],
                'duration_seconds': duration_seconds
            })

    # Group durations by resistance and support lines and calculate min, max, avg
    grouped_durations = {}
    for entry in durations:
        key = (entry['resistance_equation'], entry['support_equation'])
        if key not in grouped_durations:
            grouped_durations[key] = []
        grouped_durations[key].append(entry['duration_seconds'])

    summary_durations = []
    for (r_eq, s_eq), secs in grouped_durations.items():
        summary_durations.append({
            'resistance_equation': r_eq,
            'support_equation': s_eq,
            'min_duration_seconds': min(secs),
            'max_duration_seconds': max(secs),
            'avg_duration_seconds': sum(secs) / len(secs),
            'num_occurrences': len(secs)
        })

    return summary_durations




def predict_next_move(df, current_price_point, active_resistance, active_support, first_timestamp, breakout_status='none'):
    current_relative_timestamp = (current_price_point.name.timestamp() - first_timestamp.timestamp())

    print("\n--- Next Move Prediction ---")

    if breakout_status == 'up_breakout':
        print("The price has broken above all identified resistance lines. This indicates a strong uptrend.")
        print("Potential for continued upward movement. New resistance levels may form higher.")
        return
    elif breakout_status == 'down_breakout':
        print("The price has broken below all identified support lines. This indicates a strong downtrend.")
        print("Potential for continued downward movement. New support levels may form lower.")
        return
    elif breakout_status == 'outside_all':
        print("The price is currently outside all identified support and resistance channels.")
        print("This could indicate a strong trend, or a period of high volatility.")
        return
    
    if not active_resistance or not active_support:
        print("No clear active channel found for prediction.")
        return

    # --- Indicator-based Prediction ---
    latest_indicators = df.iloc[-1]
    rsi = latest_indicators.get('rsi')
    macd = latest_indicators.get('MACD') # Use 'MACD' as per DataFrame columns
    short_sma = latest_indicators.get('short_sma') # Use 'short_sma'
    volume = latest_indicators.get('volume') # Add volume
    price = current_price_point['price']

    score = 0
    reasons = []

    # RSI
    if rsi is not None:
        if rsi > 70:
            score -= 2
            reasons.append(f"RSI ({rsi:.2f}) is overbought (> 70)")
        elif rsi < 30:
            score += 2
            reasons.append(f"RSI ({rsi:.2f}) is oversold (< 30)")
        else:
            score += 0
            reasons.append(f"RSI ({rsi:.2f}) is neutral")


    # MACD
    if macd is not None:
        if macd > 0:
            score += 1
            reasons.append(f"MACD ({macd:.2f}) is bullish (> 0)")
        else:
            score -= 1
            reasons.append(f"MACD ({macd:.2f}) is bearish (< 0)")

    # SMA
    if short_sma is not None:
        if price > short_sma:
            score += 1
            reasons.append(f"Price ({price:.2f}) is above Short SMA ({short_sma:.2f})")
        else:
            score -= 1
            reasons.append(f"Price ({price:.2f}) is below Short SMA ({short_sma:.2f})")

    # Volume (simple check: high volume with price movement)
    if volume is not None and df['volume'].mean() > 0: # Avoid division by zero if mean is 0
        avg_volume = df['volume'].mean()
        if volume > avg_volume * 1.5: # If current volume is 50% higher than average
            reasons.append(f"Volume ({volume:.2f}) is high (>{avg_volume * 1.5:.2f})")

    # Channel Position
    r_y = active_resistance[0]['slope'] * current_relative_timestamp + active_resistance[0]['intercept']
    s_y = active_support[0]['slope'] * current_relative_timestamp + active_support[0]['intercept']
    if price > (r_y + s_y) / 2:
        score -= 0.5
        reasons.append(f"Price ({price:.2f}) is in the upper half of the channel (midpoint: {((r_y + s_y) / 2):.2f})")
    else:
        score += 0.5
        reasons.append(f"Price ({price:.2f}) is in the lower half of the channel (midpoint: {((r_y + s_y) / 2):.2f})")


    print("Prediction Score:", score)
    print("Reasons:")
    for reason in reasons:
        print("- ", reason)

    if score > 1:
        print("\nPrediction: The price is likely to go UP.")
        return "up"
    elif score < -1:
        print("\nPrediction: The price is likely to go DOWN.")
        return "down"
    else:
        print("\nPrediction: The price is likely to remain NEUTRAL or in a consolidation phase.")
        return "neutral"

    print("----------------------------")

def auto_discover_percentage_change(df, first_timestamp, min_percent=0.001, max_percent=0.1, step=0.001):
    best_percentage = None
    best_score = -1

    for pc in [i / 1000 for i in range(int(min_percent * 1000), int(max_percent * 1000) + int(step * 1000), int(step * 1000))]:
        swing_highs_df, swing_lows_df = find_swing_points(df, percentage_change=pc)

        if not swing_highs_df.empty and not swing_lows_df.empty:
            resistance_lines = find_support_resistance_lines(swing_highs_df, 'resistance', first_timestamp)
            support_lines = find_support_resistance_lines(swing_lows_df, 'support', first_timestamp)

            if resistance_lines and support_lines:
                total_r_value = 0
                for line in resistance_lines + support_lines:
                    total_r_value += abs(line['r_value'])
                
                avg_r_value = total_r_value / (len(resistance_lines) + len(support_lines))
                
                num_lines = len(resistance_lines) + len(support_lines)
                
                line_penalty = 0
                if num_lines > 20: # If more than 20 lines, start penalizing
                    line_penalty = (num_lines - 20) * 0.1 # Penalty per line

                line_count_reward = 0
                if 2 <= num_lines <= 20:
                    line_count_reward = 0.2 # Reward for being in the sweet spot

                score = avg_r_value + line_count_reward - line_penalty

                if score > best_score:
                    best_score = score
                    best_percentage = pc

    return best_percentage
