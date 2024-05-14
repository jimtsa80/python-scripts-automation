from azure.storage.blob import ContainerClient
import argparse
import time

def download_blobs(container_name, credential):
    cc = ContainerClient(account_url="https://isieve.blob.core.windows.net", container_name=container_name, credential=credential)

    start_time = time.time()

    try:
        # Example - Download all blobs in the container:
        for blob in cc.list_blobs():
            blob_name = blob.name
            with open(blob_name, "wb") as my_blob:
                download_blob = cc.download_blob(blob_name)
                download_blob.readinto(my_blob)
    except Exception as e:
        print("Error:", e)
        return

    end_time = time.time()

    total_time_seconds = end_time - start_time
    total_time_minutes = total_time_seconds // 60
    total_time_seconds %= 60

    print("Total time taken for download: {:.0f} minutes {:.2f} seconds".format(total_time_minutes, total_time_seconds))

def main():
    parser = argparse.ArgumentParser(description='Download blobs from Azure Blob Storage container')
    parser.add_argument('container_name', type=str, help='Name of the Azure Blob Storage container')
    args = parser.parse_args()

    try:
        with open('creds.txt', 'r') as file:
            credential = file.read().strip()
    except Exception as e:
        print("Error reading credentials file:", e)
        return

    download_blobs(args.container_name, credential)

if __name__ == "__main__":
    main()