import pandas as pd
import re
import pyperclip

# URL of the ESPN roster page
url = "https://www.espn.com/mlb/team/roster/_/name/sf/san-francisco-giants"

# Use pandas to read the tables from the page
tables = pd.read_html(url)

# Regular expression to capture the name and number
name_number_pattern = re.compile(r'([^\d]+)(\d+)')

# Collect the output in a list
output_list = []

for table in tables:
    if 'Name' in table.columns:
        player_names = table['Name']
        
        for name in player_names:
            match = name_number_pattern.match(name)
            if match:
                player_name = match.group(1).strip()
                player_number = match.group(2)
                output_list.append(f"{player_number} - {player_name}")
            else:
                output_list.append(f"Could not parse name: {name}")

# Join the output into a single string and copy to clipboard
output_text = "\n".join(output_list)
pyperclip.copy(output_text)

print("Player list copied to clipboard!")
