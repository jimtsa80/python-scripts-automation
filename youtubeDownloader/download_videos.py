import sys
from yt_dlp import YoutubeDL

def download_video(url):
    try:
        print(f"Processing: {url}")
        # List available formats
        print("Fetching available formats...")
        ydl_opts = {'listformats': True}
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=False)
        
        # Prompt user to select a format
        format_id = input("Enter the format ID to download: ").strip()
        
        # Download the selected format
        print("Downloading...")
        ydl_opts = {'format': format_id, 'outtmpl': '%(title)s.%(ext)s'}
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("Download completed!")
    except Exception as e:
        print(f"Failed to download video from {url}. Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_downloader.py <YouTube_URL>")
        sys.exit(1)

    url = sys.argv[1]
    download_video(url)
