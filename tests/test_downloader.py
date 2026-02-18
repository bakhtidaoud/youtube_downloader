import pytest
from unittest.mock import MagicMock, patch
import downloader
from downloader import is_valid_url, format_bytes, DownloadProgress

def test_is_valid_url():
    assert is_valid_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_url("http://github.com") is True
    assert is_valid_url("not a url") is False
    assert is_valid_url("") is False
    assert is_valid_url(None) is False

def test_format_bytes():
    assert format_bytes(500) == "500.00B"
    assert format_bytes(1024) == "1.00KB"
    assert format_bytes(1024 * 1024) == "1.00MB"
    assert format_bytes(1024 * 1024 * 1024) == "1.00GB"
    assert format_bytes(0) == "N/A"
    assert format_bytes(None) == "N/A"

@patch('yt_dlp.YoutubeDL')
def test_get_video_info_mock(mock_ytdl):
    # Setup mock
    instance = mock_ytdl.return_value.__enter__.return_value
    instance.extract_info.return_value = {'title': 'Mock Video', 'id': '123'}
    
    result = downloader.get_video_info("https://fake-url.com")
    
    assert result['title'] == 'Mock Video'
    assert result['id'] == '123'
    instance.extract_info.assert_called_once_with("https://fake-url.com", download=False)

@patch('yt_dlp.YoutubeDL')
def test_download_item_mock(mock_ytdl):
    instance = mock_ytdl.return_value.__enter__.return_value
    
    # Just ensure it calls download without error
    downloader.download_item("https://fake-url.com", format_id="720p")
    
    instance.download.assert_called_once_with(["https://fake-url.com"])
    # Check if correct opts were passed (can be complex, but let's check format)
    args, kwargs = mock_ytdl.call_args
    assert 'bestvideo[height<=720]+bestaudio/best' in args[0]['format']
