import os

# Define the directory containing the files
directory = 'csvs'  # Change this to your folder path

# Iterate through each file in the directory
for filename in os.listdir(directory):
    # Define the old file path
    old_file_path = os.path.join(directory, filename)
    
    # Only process files (not directories)
    if os.path.isfile(old_file_path):
        # Replace '_-_' with '' and '_&_' with '&'
        new_filename = filename.replace('_-_', '').replace('_&_', '').replace('.zip', '')
        
        # Check if the filename starts with 'reduced_' and add 'batters_' at the beginning
        if new_filename.startswith('reduced_'):
            new_filename = 'batters_' + new_filename
        
        # Define the new file path
        new_file_path = os.path.join(directory, new_filename)
        
        # Rename the file
        os.rename(old_file_path, new_file_path)

print("Files have been renamed successfully.")