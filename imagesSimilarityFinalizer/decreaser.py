import pandas as pd
import numpy as np
import sys

if len(sys.argv) < 2:
    print('Usage: python reduce_duration.py input.xlsx [output.xlsx]')
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2] if len(sys.argv) > 2 else 'output.xlsx'

df = pd.read_excel(input_file)
dur = df['Duration']

# --- Percentage of total you want to keep (e.g. 0.55 for ~55%) --- #
ratio = 0.40

sum0 = dur.sum()
N = len(dur)
target_sum = sum0 * ratio

# Base decrease per row:
base_decrease = (sum0 - target_sum) / N

# Add random noise around the base_decrease (e.g. ±10%)
random_factors = np.random.uniform(0.9, 1.1, size=N)   # 10% up/down
decreases = base_decrease * random_factors

# Apply, round, and clip below zero
new_dur = np.round(dur - decreases).clip(lower=2).astype(int)
df['Duration'] = new_dur

print(f"Base decrease per row: {base_decrease:.2f}")
print(f"Original sum: {sum0:.2f}, New sum: {df['Duration'].sum():.2f}")
print(f"Approximate ratio: {df['Duration'].sum() / sum0:.2f}")

df.to_excel(output_file, index=False)
print(f'Done. Saved to {output_file}')