import sys
import os
import yt_dlp

def progress_hook(d):
    """
    Callback function used by yt-dlp to report download progress.
    """
    if d['status'] == 'downloading':
        # Safely extract progress details
        percent = d.get('_percent_str', '0%').strip()
        speed = d.get('_speed_str', 'N/A').strip()
        eta = d.get('_eta_str', 'N/A').strip()
        
        # Clear the current line and print updated progress
        sys.stdout.write(f"\r🚀 Downloading... {percent} | Speed: {speed} | ETA: {eta}")
        sys.stdout.flush()
        
    elif d['status'] == 'finished':
        filename = d.get('filename', 'the file')
        print(f"\n✨ Successfully downloaded: {os.path.basename(filename)}")

def download_video(url: str):
    """
    Downloads a video from the given URL using the best quality.
    """
    # Ensure the downloads directory exists
    download_dir = 'downloads'
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # yt-dlp configuration options
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Merges best video and best audio
        'outtmpl': f'{download_dir}/%(title)s.%(ext)s',  # Save structure
        'progress_hooks': [progress_hook],
        'quiet': True,                        # Suppress clutter, we use our hook
        'no_warnings': True,
        'merge_output_format': 'mp4',         # Standard accessible format
    }

    print(f"🔍 Analyzing URL: {url}...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        print(f"\n❌ Error: The URL might be invalid or there are network issues.\nDetails: {str(e)}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <URL>")
        sys.exit(1)
    
    target_url = sys.argv[1]
    download_video(target_url)
