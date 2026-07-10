import sys
import re

# Function to extract and format the names
def extract_names(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Extract lines in the desired format (non-empty lines with valid characters)
        names = [line.strip() for line in lines if line.strip()]
        
        # Sort and format the output
        names.sort()
        output = f"names: {names}"

        # Write output to a text file
        with open('output.txt', 'w') as output_file:
            output_file.write(output)

        print("Names extracted and written to output.txt")

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Main function to handle command-line arguments
def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_file.txt>")
        return

    input_file = sys.argv[1]
    extract_names(input_file)

if __name__ == "__main__":
    main()
