import pandas as pd
import re

# URL of the ESPN roster page
url = "https://www.espn.com/mlb/team/roster/_/name/sf/san-francisco-giants"

# Use pandas to read the tables from the page
tables = pd.read_html(url)

# Check the number of tables found
print(f"Number of tables found: {len(tables)}\n")

# Regular expression to capture the name and number
name_number_pattern = re.compile(r'([^\d]+)(\d+)')

# Iterate through each table and apply regex to extract number and name
for i, table in enumerate(tables):
    #print(f"Table {i + 1}:")
    
    if 'Name' in table.columns:
        player_names = table['Name']
        
        for name in player_names:
            match = name_number_pattern.match(name)
            if match:
                player_name = match.group(1).strip()
                player_number = match.group(2)
                print(f"{player_number} - {player_name}")
            else:
                print(f"Could not parse name: {name}")
    
    #print()  # For spacing between tables


