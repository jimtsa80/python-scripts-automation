#!/bin/sh

# Ensure the correct number of arguments are provided
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <input_zip> <num_parts>"
  exit 1
fi

# Assign arguments to variables
input_zip=$1
num_parts=$2

# Run the Java program with the provided arguments
java ZipSplitter "$input_zip" "$num_parts"