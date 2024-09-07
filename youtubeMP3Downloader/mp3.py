import ffmpeg
import os

# Directory containing subdirectories with .mp4 and .f140.m4a files
root_dir = '.'  # Replace with your root directory

def convert_audio_to_mp3(input_file, output_file):
    try:
        # Extract the audio and convert it to MP3
        ffmpeg.input(input_file).output(output_file, codec='libmp3lame').run()
        print(f'Converted {input_file} to {output_file}')
    except ffmpeg._run.Error as e:
        print(f'Error converting {input_file}: {e}')

def process_directory(directory):
    print(f'Scanning directory: {directory}')  # Print the current directory being scanned
    for root, dirs, files in os.walk(directory):
        print(f'Found directory: {root}')  # Print directories found
        for file_name in files:
            print(f'Found file: {file_name}')  # Print files found
            # Check for .f140.m4a or .mp4 files
            if file_name.endswith('.f140.m4a') or file_name.endswith('.mp4'):
                input_path = os.path.join(root, file_name)
                output_path = os.path.join(root, file_name.rsplit('.', 2)[0] + '.mp3')
                print(f'Preparing to convert: {input_path} to {output_path}')  # Print conversion details
                convert_audio_to_mp3(input_path, output_path)

# Start processing from the root directory
process_directory(root_dir)
