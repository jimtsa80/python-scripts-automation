from azure.storage.blob import ContainerClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
import argparse
import time
import os

def bytes_to_gb(size_in_bytes):
    return round(size_in_bytes / (1024 ** 3), 2)

def download_blob_with_retry(container_client, blob_name):
    max_retries = 3
    for attempt in range(max_retries):
        start_time = time.time()
        try:
            with open(blob_name, "wb") as my_blob:
                download_blob = container_client.download_blob(blob_name)
                download_blob.readinto(my_blob)
            end_time = time.time()
            time_taken = end_time - start_time
            file_size = os.path.getsize(blob_name)
            download_speed = file_size / time_taken  # Speed in bytes per second
            print("Time taken to download {}: {:.0f} minutes {:.2f} seconds".format(blob_name, time_taken // 60, time_taken % 60))
            print("Download speed: {:.2f} bytes/second".format(download_speed))
            return True  # Download successful, exit the loop
        except ResourceNotFoundError as e:
            print("Blob not found:", e)
            return False  # No need to retry, exit the loop
        except Exception as e:
            print("Error downloading blob (attempt {}):".format(attempt + 1), e)
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(1)  # Wait for a moment before retrying
    return False  # All retries failed


def list_and_get_total_size(cc, target_string):
    total_size = 0
    files_to_download = []

    try:
        # Example - List blobs with target string in the name:
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
        print("- {}. {}".format(i, file))
    print("Total size of files to be downloaded: {:.2f} GB".format(bytes_to_gb(total_size)))

    try:
        # Example - Download blobs with target string in the name:
        for i, blob_name in enumerate(files_to_download, 1):
            # Print filename, date, and size
            print("\nFile Name:", blob_name)
            blob_properties = cc.get_blob_client(blob_name).get_blob_properties()
            print("Last Modified:", blob_properties['last_modified'])
            print("Size:", bytes_to_gb(blob_properties['size']), "GB")

            # Download the blob with retry
            try:
                success = download_blob_with_retry(cc, blob_name)
                if not success:
                    print("Download failed for blob:", blob_name)
            except ResourceExistsError as e:
                print("Blob already exists:", e)

            # Display download progress
            print("({}/{})".format(i, len(files_to_download)), end=' ')

    except Exception as e:
        print("Error:", e)
        return

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

