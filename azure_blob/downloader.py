from azure.storage.blob import BlobServiceClient

def download_blob(storage_connection_string, container_name, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    
    with open(blob_name, "wb") as file:
        file.write(blob_client.download_blob().readall())

# Set the connection string, container name, blob name
storage_connection_string = "isieve.blob.core.windows.net"
container_name = "test" # container in which file is being stored
blob_name = "000004.jpg" # file which you need to download

# Download the blob
download_blob(storage_connection_string, container_name, blob_name)
