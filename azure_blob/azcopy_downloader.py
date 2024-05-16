import subprocess
import argparse
import os
import traceback
from azure.storage.blob import ContainerClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from pathlib import Path
import time

def bytes_to_gb(size_in_bytes):
    return round(size_in_bytes / (1024 ** 3), 2)

def download_blob_with_azcopy(source_url, destination_path, sas_token, blob_name):
    # AzCopy command to download the blob
    source_url = f"{source_url.rstrip('/')}/{blob_name}{sas_token}"
    destination_directory = Path(destination_path) / blob_name
    source_url = str(source_url)

    azcopy_command = [
        "azcopy",
        "copy",
        source_url,
        str(destination_directory),
        "--recursive=true"
    ]

    # Execute AzCopy command
    subprocess.run(azcopy_command, check=True)

def list_and_get_total_size(cc, target_string):
    total_size = 0
    files_to_download = []

    try:
        for blob in cc.list_blobs():
            if target_string in blob.name:
                files_to_download.append(blob.name)
                total_size += blob.size
    except Exception as e:
        print("Error listing blobs:", e)
        return None, 0

    return files_to_download, total_size

def download_blobs(container_name, credential, target_string):
    cc = ContainerClient(account_url="https://isieve.blob.core.windows.net", container_name=container_name, credential=credential)

    files_to_download, total_size = list_and_get_total_size(cc, target_string)

    if files_to_download is None:
        print("Error occurred while listing blobs.")
        return

    print("Files to be downloaded ({:d} files):".format(len(files_to_download)))
    for i, file in enumerate(files_to_download, 1):
        file_size = bytes_to_gb(cc.get_blob_client(file).get_blob_properties()['size'])
        print("- {}. {} ({} GB)".format(i, file, file_size))
    print("Total size of files to be downloaded: {:.2f} GB".format(bytes_to_gb(total_size)))

    start_time = time.time()
    try:
        for blob_name in files_to_download:
            try:
                download_blob_with_azcopy("https://isieve.blob.core.windows.net/" + container_name, os.getcwd(), credential, blob_name)
            except Exception as e:
                print("Error downloading blob:", e)
                traceback.print_exc()

    except Exception as e:
        print("Error:", e)
        return
    
    end_time = time.time()
    print("Total time taken: {:.2f} seconds".format(end_time - start_time))

def main():
    parser = argparse.ArgumentParser(description='Download blobs from Azure Blob Storage container')
    parser.add_argument('container_name', type=str, help='Name of the Azure Blob Storage container')
    parser.add_argument('target_string', type=str, help='Target string to search in blob names')
    args = parser.parse_args()

    try:
        with open('creds.txt', 'r') as file:
            credential = file.read().strip()
    except Exception as e:
        print("Error reading credentials file:", e)
        return

    download_blobs(args.container_name, credential, args.target_string)

if __name__ == "__main__":
    main()
