import os
import pyperclip

# Function to generate the PowerShell command string
def generate_powershell_command(filename):
    # Keep the original filename for the first {file} placeholder
    original_filename = filename
    
    # Remove "HP_" prefix and ".xlsx" extension for the second {file} placeholder
    if filename.startswith("HP_"):
        modified_filename = filename[3:-5]  # Remove "HP_" and ".xlsx"
    else:
        modified_filename = filename[:-5]   # Remove ".xlsx"
    
    # Create the PowerShell command
    command = f'powershell -ExecutionPolicy Bypass -File .\\run.ps1 -filePath ".\\{original_filename}" -sequencesInfoPath "C:\\Users\\jimtsa\\Desktop\\python-scripts-automation\\imagesSimilarity\\toBeFinalized\\{modified_filename}\\sequences_info.xlsx"'
    return command

# Get the current directory (where the script is located)
current_dir = os.path.dirname(os.path.abspath(__file__))

# List to store all the generated commands
commands = []

# Iterate over all files in the directory
for file in os.listdir(current_dir):
    # Process only .xlsx files
    if file.endswith(".xlsx"):
        # Generate the command
        command = generate_powershell_command(file)
        # Add the command to the list
        commands.append(command)

# Join all the commands into a single string separated by newlines
final_commands = "\n".join(commands)

# Copy the final result to the clipboard
pyperclip.copy(final_commands)

# Print the final result (optional)
print(final_commands)
