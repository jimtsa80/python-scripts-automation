import pandas as pd
import matplotlib.pyplot as plt
import sys

def analyze_duration_distribution(file_path, brand, location):
    # Load the data from the Excel file
    df = pd.read_excel(file_path)

    # Filter the DataFrame for the specified Brand and Location
    filtered_df = df[(df['Brand'] == brand) & (df['Location'] == location)]

    # Convert the duration column to numeric (assuming it's formatted as strings)
    filtered_df['Duration'] = pd.to_numeric(filtered_df['Duration'], errors='coerce')

    # Group by Sequence Frame Number and sum the durations
    distribution = filtered_df.groupby('Sequence Frame Number')['Duration'].sum().reset_index()

    # Visualize the distribution
    plt.figure(figsize=(10, 6))
    plt.bar(distribution['Sequence Frame Number'].astype(str), distribution['Duration'], color='skyblue')
    plt.xlabel('Sequence Frame Number')
    plt.ylabel('Total Duration')
    plt.title(f'Duration Distribution of {brand} at {location}')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <file_path> <brand> <location>")
    else:
        file_path = sys.argv[1]
        brand = sys.argv[2]
        location = sys.argv[3]
        analyze_duration_distribution(file_path, brand, location)
