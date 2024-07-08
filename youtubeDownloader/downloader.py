import yt_dlp

# URL of the YouTube channel
channel_url = 'https://www.youtube.com/@alexandermurray1680'

# Options for yt-dlp
ydl_opts = {
    'format': 'best',  # Download the best quality available
    'outtmpl': '%(title)s.%(ext)s',  # Save files using the video title
    'restrictfilenames': True,  # Restrict filenames to ASCII characters and remove special characters
    'noplaylist': False,  # Ensure the channel's playlist of videos is downloaded
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    # Download all videos from the channel
    ydl.download([channel_url])
