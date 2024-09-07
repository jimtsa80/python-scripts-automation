import yt_dlp

# Options for downloading
ydl_opts = {
    'format': 'bestvideo+bestaudio/best',  # Choose the best video and audio combination
    'outtmpl': '%(playlist_title)s/%(title)s.%(ext)s',
    'noplaylist': False,
    'ignoreerrors': True,  # Continue with the rest of the playlist if an error occurs
}

def download_playlist(url):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.ExtractorError as e:
        print(f'Error occurred: {e}')
        # Optionally, handle specific errors or retry logic here
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        # Handle any other unexpected errors here

def download_playlists_from_file(file_path):
    try:
        # Read the file containing URLs
        with open(file_path, 'r') as file:
            urls = file.readlines()

        # Process each URL in the file
        for url in urls:
            url = url.strip()  # Remove any leading/trailing spaces or newline characters
            if url:
                print(f"Downloading playlist: {url}")
                download_playlist(url)

    except FileNotFoundError:
        print(f'File not found: {file_path}')
    except Exception as e:
        print(f'An error occurred: {e}')

# Specify the file path to the text file containing playlist URLs
file_path = 'playlists.txt'

# Download playlists listed in the file
download_playlists_from_file(file_path)
