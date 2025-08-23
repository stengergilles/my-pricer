import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def generate_chart(df, resistance_lines, support_lines, active_resistance, active_support, crypto_id, filename):
    plt.figure(figsize=(12, 7))
    plt.plot(df.index, df['price'], label='Price', color='blue')

    x_start = df.index[0]
    x_end = df.index[-1]

    # Plot resistance lines
    for i, line in enumerate(resistance_lines):
        y_start = line['slope'] * ((x_start.timestamp() - df.index[0].timestamp())) + line['intercept']
        y_end = line['slope'] * ((x_end.timestamp() - df.index[0].timestamp())) + line['intercept']
        
        is_active = (line == active_resistance)
        color = 'red' if is_active else 'lightcoral'
        linestyle = '-' if is_active else '--'
        linewidth = 2 if is_active else 1
        label = 'Active Resistance' if is_active else ('Resistance' if i == 0 else None)

        plt.plot([x_start, x_end], [y_start, y_end], color=color, linestyle=linestyle, linewidth=linewidth, label=label)

    # Plot support lines
    for i, line in enumerate(support_lines):
        y_start = line['slope'] * ((x_start.timestamp() - df.index[0].timestamp())) + line['intercept']
        y_end = line['slope'] * ((x_end.timestamp() - df.index[0].timestamp())) + line['intercept']

        is_active = (line == active_support)
        color = 'green' if is_active else 'lightgreen'
        linestyle = '-' if is_active else '--'
        linewidth = 2 if is_active else 1
        label = 'Active Support' if is_active else ('Support' if i == 0 else None)
        
        plt.plot([x_start, x_end], [y_start, y_end], color=color, linestyle=linestyle, linewidth=linewidth, label=label)


    plt.title(f'{crypto_id.capitalize()} Price Chart')
    plt.xlabel('Date')
    plt.ylabel('Price (USD)')
    plt.legend()
    plt.grid(True)
    os.makedirs(filename.parent, exist_ok=True) # Ensure directory exists
    plt.savefig(filename)
    plt.close()
    print(f"Chart saved as {filename}")
