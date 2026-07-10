import os
import subprocess
import sys
import glob

def extract_frames(input_folder):
    # Ensure the provided folder exists
    if not os.path.isdir(input_folder):
        print(f"Error: Folder '{input_folder}' does not exist.")
        return

    # Find all MP4 files in the input folder
    mp4_files = glob.glob(os.path.join(input_folder, "*.mp4"))

    if not mp4_files:
        print("No MP4 files found in the folder.")
        return

    for mp4_file in mp4_files:
        base_name = os.path.splitext(os.path.basename(mp4_file))[0]  # Remove .mp4 extension
        output_pattern = os.path.join(input_folder, f"{base_name}_%05d.jpg")

        # FFmpeg command with all possible fixes
        ffmpeg_cmd = [
            "ffmpeg",
            "-hwaccel", "none",                     # Disable GPU decoding (fix green frames)
            "-vsync", "vfr",                        # Avoid duplicate/missing frames
            "-fflags", "+discardcorrupt",           # Skip corrupt frames
            "-err_detect", "ignore_err",            # Ignore decoding errors
            "-i", mp4_file,                         # Input file
            "-vf", "yadif,fps=1",                   # Removing `pp7,unsharp` (test stability)
            "-pix_fmt", "bgr24",                    # Safe pixel format
            "-q:v", "2",                            # High-quality images
            "-an",                                   # Disable audio processing
            output_pattern                          # Output file pattern
        ]

        # Run ffmpeg command
        subprocess.run(ffmpeg_cmd, check=True)

    print("Frame extraction completed.")

# Check if script was given a folder as an argument
if len(sys.argv) != 2:
    print("Usage: python script.py /path/to/mp4/folder")
else:
    input_folder = sys.argv[1]
    extract_frames(input_folder)
