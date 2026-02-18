import sys
import os
import re
import logging
import yt_dlp
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("UltraTube.Downloader")
_METADATA_CACHE = {}

try:
    import browser_cookie3
except ImportError:
    browser_cookie3 = None

class DownloadProgress:
    """Structure to hold progress data for listeners."""
    def __init__(self, status, percentage=0, speed="0B/s", eta="00:00", title="Unknown", filename=None):
        self.status = status
        self.percentage = percentage
        self.speed = speed
        self.eta = eta
        self.title = title
        self.filename = filename

def create_progress_hook(external_callback=None):
    """Creates a hook function for yt-dlp that reports to an optional callback."""
    def hook(d):
        progress_data = DownloadProgress(status=d['status'])
        
        if d['status'] == 'downloading':
            p_str = d.get('_percent_str', '0%').replace('%', '').strip()
            try:
                progress_data.percentage = float(p_str)
            except ValueError:
                progress_data.percentage = 0.0
                
            progress_data.speed = d.get('_speed_str', 'N/A').strip()
            progress_data.eta = d.get('_eta_str', 'N/A').strip()
            progress_data.title = d.get('info_dict', {}).get('title', 'Unknown')
            
            if not external_callback:
                sys.stdout.write(f"\r🚀 [{progress_data.title[:20]}...] {progress_data.percentage}% @ {progress_data.speed} | ETA: {progress_data.eta}          ")
                sys.stdout.flush()
                
        elif d['status'] == 'finished':
            progress_data.filename = d.get('filename')
            if not external_callback:
                print(f"\n✨ Finished: {os.path.basename(progress_data.filename)}")

        if external_callback:
            external_callback(progress_data)
            
    return hook

def format_bytes(size):
    """Convert bytes to human readable format."""
    if not size: return "N/A"
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size >= power:
        size /= power
        n += 1
    return f"{size:.2f}{power_labels[n]}B"

def is_valid_url(url):
    """Basic URL validation for video links."""
    if not url: return False
    # Simple regex for http/https URLs
    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

def get_video_info(url, cookie_file=None, browser=None, proxy=None, internal_browser=False, **kwargs):
    """Fetch metadata, supports cookies for private videos and proxies."""
    # 1. Simple Cache Check
    if url in _METADATA_CACHE:
        logger.info(f"Using cached metadata for: {url}")
        return _METADATA_CACHE[url]

    ydl_opts = {
        'quiet': True, 
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'socket_timeout': 30,  # 30 seconds timeout
        'retries': 10,        # Retry up to 10 times
        'allow_unplayable_formats': kwargs.get('allow_unplayable', False),
    }
    
    if internal_browser:
        # Point to our embedded browser's cookie storage
        cookie_path = os.path.abspath(os.path.join(os.getcwd(), "browser_data", "Cookies"))
        if os.path.exists(cookie_path):
            ydl_opts['cookiefile'] = cookie_path
    elif cookie_file:
        ydl_opts['cookiefile'] = cookie_file
    elif browser:
        ydl_opts['cookiesfrombrowser'] = (browser,)
    
    if proxy:
        ydl_opts['proxy'] = proxy

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(url, download=False)
            _METADATA_CACHE[url] = res
            return res
    except Exception as e:
        logger.error(f"Error fetching info for {url}: {e}")
        return None

def download_item(url, format_id=None, download_dir='downloads', sub_lang=None, write_thumbnail=False, progress_callback=None, cookie_file=None, browser=None, proxy=None, internal_browser=False, allow_unplayable=False, cdm_path=None):
    """Worker function with support for high-fidelity formats (8K, HDR, 360) and DRM."""
    
    # Advanced logic for quality selection based on format_id
    # format_id can be a specific ID from yt-dlp OR a descriptive string from our UI
    if format_id == "Best Available" or not format_id:
        selected_format = 'bestvideo+bestaudio/best'
    elif "8K" in format_id:
        selected_format = 'bestvideo[height<=4320]+bestaudio/best'
    elif "4K HDR" in format_id:
        # Prefer VP9.2 which carries HDR metadata for YouTube
        selected_format = 'bestvideo[height<=2160][vcodec^=vp9.2]+bestaudio/best'
    elif "4K" in format_id:
        selected_format = 'bestvideo[height<=2160]+bestaudio/best'
    elif "1440p" in format_id:
        selected_format = 'bestvideo[height<=1440]+bestaudio/best'
    elif "1080p" in format_id:
        selected_format = 'bestvideo[height<=1080]+bestaudio/best'
    elif "720p" in format_id:
        selected_format = 'bestvideo[height<=720]+bestaudio/best'
    elif "480p" in format_id:
        selected_format = 'bestvideo[height<=480]+bestaudio/best'
    else:
        # Fallback for specific format IDs (e.g. from a list)
        selected_format = format_id if '+' in format_id or '/' in format_id else f"{format_id}+bestaudio/best"

    ydl_opts = {
        'format': selected_format,
        'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
        'progress_hooks': [create_progress_hook(progress_callback)],
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'download_archive': 'archive.txt',
        'writesubtitles': sub_lang is not None,
        'subtitleslangs': [sub_lang] if sub_lang and sub_lang != 'all' else ['all'],
        'postprocessors': [],
        'socket_timeout': 30,
        'retries': 15,
        'fragment_retries': 15,
        'allow_unplayable_formats': allow_unplayable,
        'writemetadata': True,
        'xattrs': True,  # Help preserve metadata on supported filesystems
        'prefer_ffmpeg': True,
    }
    
    # Metadata preservation for 360 / VR and HDR
    # yt-dlp preserves metadata during merging by default, but we can be explicit
    ydl_opts['postprocessor_args'] = {
        'ffmpeg': [
            '-map_metadata', '0', # Copy metadata from first input
            '-movflags', '+faststart' # Good for web delivery/VR players
        ]
    }
    
    if cdm_path:
        # Experimental: Add Mp4Decrypt post-processor
        # This requires the yt-dlp-mp4decrypt plugin to be installed
        ydl_opts['postprocessors'].append({
            'key': 'Mp4Decrypt',
            'when': 'before_dl',
            'devicepath': cdm_path,
        })

    if internal_browser:
        cookie_path = os.path.abspath(os.path.join(os.getcwd(), "browser_data", "Cookies"))
        if os.path.exists(cookie_path):
            ydl_opts['cookiefile'] = cookie_path
    elif cookie_file:
        ydl_opts['cookiefile'] = cookie_file
    elif browser:
        ydl_opts['cookiesfrombrowser'] = (browser,)
    
    if proxy:
        ydl_opts['proxy'] = proxy
    
    if write_thumbnail:
        ydl_opts['writethumbnail'] = True
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegThumbnailsConvertor',
            'format': 'jpg',
        })

    if sub_lang:
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegSubtitlesConvertor',
            'format': 'srt',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Starting download: {url}")
            ydl.download([url])
            logger.info(f"Finished download: {url}")
    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")

def run_multi_download(urls, max_workers=3, progress_callback=None, **kwargs):
    """Run multiple concurrent downloads with shared session settings."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for url in urls:
            executor.submit(download_item, url, progress_callback=progress_callback, **kwargs)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("\n� Network & Auth Options (Optional):")
    proxy_url = input("🔗 Proxy URL (e.g. http://127.0.0.1:8080 or Enter to skip): ").strip() or None
    auth_choice = input("👉 1: cookies.txt, 2: Get from Browser, Enter: Skip: ").strip()
    c_file = None
    b_name = None
    
    if auth_choice == "1":
        c_file = input("📁 Enter path to cookies.txt: ").strip()
    elif auth_choice == "2":
        b_name = input("🌐 Browser (e.g., chrome, firefox, edge): ").strip().lower()

    info = get_video_info(url, c_file, b_name, proxy_url)
    if not info:
        sys.exit(1)

    is_playlist = 'entries' in info
    
    print("\n🛠  Extra Options:")
    subs = input("👉 Subtitles (lang code/all/Enter to skip): ").strip() or None
    thumb = input("👉 Thumbnail? (y/n): ").strip().lower() == 'y'

    settings = {
        'sub_lang': subs,
        'write_thumbnail': thumb,
        'cookie_file': c_file,
        'browser': b_name,
        'proxy': proxy_url
    }

    if is_playlist:
        entries = list(info['entries'])
        print(f"\n📂 Playlist/Channel: {info.get('title')}")
        limit = input(f"🔢 Total {len(entries)} videos. Limit? (Enter for ALL): ").strip()
        if limit.isdigit():
            entries = entries[:int(limit)]
        
        urls = [e['url'] for e in entries if 'url' in e]
        run_multi_download(urls, **settings)
    else:
        print(f"\n📺 Single Video: {info.get('title')}")
        formats = info.get('formats', [])
        display_formats = [f for f in formats if f.get('vcodec') != 'none' or f.get('acodec') != 'none']
        print(f"{'ID':<10} {'EXT':<6} {'RES':<12} {'FPS':<6} {'FILESIZE':<10} {'CODEC'}")
        print("-" * 60)
        valid_ids = []
        for f in display_formats:
            fid = f.get('format_id')
            res = f.get('resolution') or f"{f.get('width')}x{f.get('height')}" if f.get('width') else "audio only"
            size = format_bytes(f.get('filesize') or f.get('filesize_approx'))
            print(f"{fid:<10} {f.get('ext'):<6} {res:<12} {f.get('fps',''):<6} {size:<10} V:{f.get('vcodec','')[:5]} A:{f.get('acodec','')[:5]}")
            valid_ids.append(fid)

        choice = input("\n🔢 Enter Format ID (Enter for best): ").strip()
        download_item(url, choice if choice in valid_ids else None, **settings)
