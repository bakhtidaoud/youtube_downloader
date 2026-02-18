# UltraTube Downloader

A premium video downloader application built with Python, PyQt6, and yt-dlp.

## Features
- Download videos from YouTube and other platforms.
- High-quality video and audio merging using FFmpeg.
- Sleek and modern GUI.

## Setup
1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the virtual environment:
   - Windows: `.\venv\Scripts\activate`
   - Unix/macOS: `source venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. **Note:** Ensure you have [FFmpeg](https://ffmpeg.org/download.html) installed on your system and added to your PATH.

## Running the app
```bash
python main.py
```

## Structure
- `src/`: Source code.
- `assets/`: Images, icons, and styles.
- `downloads/`: Default download location.
- `tests/`: Unit tests.
- `main.py`: Application entry point.
