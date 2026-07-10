import os
import argparse

# Parse optional arguments
parser = argparse.ArgumentParser(description='Clean filenames in the csvs directory.')
parser.add_argument('-sport', type=str, default=None, help='Sport key to control sport-specific renames (e.g., MLB)')
args = parser.parse_args()
is_mlb = (args.sport == 'MLB')

# Define the directory containing the files
directory = 'csvs'  # Change this to your folder path

# Iterate through each file in the directory
for filename in os.listdir(directory):
    # Define the old file path
    old_file_path = os.path.join(directory, filename)
    
    # Only process files (not directories)
    if os.path.isfile(old_file_path):
        # Replace '_-_' with '' and '_&_' with '&'
        new_filename = filename.replace('_-_', '').replace('_&_', '').replace('.zip', '').replace('--', '-').replace('_-', '-').replace('.com', '_com').replace('_part','')
        if new_filename.startswith('-') or new_filename.startswith('_'):
            new_filename = new_filename[1:]
        
        # Only for MLB: if the filename starts with 'reduced_' add 'batters_' at the beginning
        if is_mlb and new_filename.startswith('reduced_'):
            new_filename = 'batters_' + new_filename
        
        # Define the new file path
        new_file_path = os.path.join(directory, new_filename)
        
        # Rename the file
        os.rename(old_file_path, new_file_path)

print("Files have been renamed successfully.")