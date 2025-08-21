def predict_movement_magnitude(df, latest_price_point, predicted_direction, active_resistance, active_support):
    first_timestamp = df.index[0]
    latest_relative_timestamp = (latest_price_point.name.timestamp() - first_timestamp.timestamp())

    if predicted_direction == 'up' and active_resistance:
        r_y_at_latest_time = active_resistance['slope'] * latest_relative_timestamp + active_resistance['intercept']
        magnitude = r_y_at_latest_time - latest_price_point['price']
        return f"+{magnitude:.2f}" if magnitude > 0 else "0.00"
    elif predicted_direction == 'down' and active_support:
        s_y_at_latest_time = active_support['slope'] * latest_relative_timestamp + active_support['intercept']
        magnitude = latest_price_point['price'] - s_y_at_latest_time
        return f"-{magnitude:.2f}" if magnitude > 0 else "0.00"
    else:
        return "0.00"
