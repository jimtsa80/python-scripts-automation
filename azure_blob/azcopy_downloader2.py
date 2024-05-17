import subprocess
import argparse
import os
import traceback
import time

def format_time(seconds):
    minutes = seconds // 60
    seconds %= 60
    return "{:d} minutes {:.2f} seconds".format(int(minutes), seconds)

def download_blob_with_azcopy(source_url, destination_path, sas_token, blob_name):
    # AzCopy command to download the blob
    source_url = "{}/{}{}".format(source_url.rstrip('/'), blob_name, sas_token)
    destination_directory = os.path.join(destination_path, blob_name)
    source_url = str(source_url)

    azcopy_command = [
        "azcopy",
        "copy",
        source_url,
        str(destination_directory),
        "--recursive=true"
    ]

    # Execute AzCopy command
    subprocess.call(azcopy_command, shell=True)

def main():
    parser = argparse.ArgumentParser(description='Download blobs from Azure Blob Storage container')
    parser.add_argument('source_url', type=str, help='Source URL of the Azure Blob Storage container')
    parser.add_argument('blob_name', type=str, help='Name of the blob to download')
    parser.add_argument('sas_token', type=str, help='SAS token for authentication')
    args = parser.parse_args()

    try:
        start_time = time.time()
        download_blob_with_azcopy(args.source_url, os.getcwd(), args.sas_token, args.blob_name)
        end_time = time.time()
        total_time_seconds = end_time - start_time
        print("Total time taken:", format_time(total_time_seconds))
    except Exception as e:
        print("Error downloading blob:", e)
        traceback.print_exc()

if __name__ == "__main__":
    main()

