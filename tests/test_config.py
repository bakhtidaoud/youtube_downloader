import os
import json
import pytest
from src.config_manager import ConfigManager, AppConfig

def test_config_load_default(tmp_path):
    config_file = tmp_path / "config.json"
    manager = ConfigManager(str(config_file))
    
    # Should be default settings
    assert manager.config.download_folder == "downloads"
    assert manager.config.dark_mode is True
    assert manager.config.max_concurrent == 3

def test_config_save_and_load(tmp_path):
    config_file = tmp_path / "config.json"
    manager = ConfigManager(str(config_file))
    
    # Update some settings
    manager.update(download_folder="custom_dl", dark_mode=False, max_concurrent=5)
    
    # Create a new manager instance to reload from file
    new_manager = ConfigManager(str(config_file))
    assert new_manager.config.download_folder == "custom_dl"
    assert new_manager.config.dark_mode is False
    assert new_manager.config.max_concurrent == 5

def test_config_smart_mode_persistence(tmp_path):
    config_file = tmp_path / "config.json"
    manager = ConfigManager(str(config_file))
    
    manager.update(smart_mode=True, last_format="MP3 Audio", last_quality="High")
    
    new_manager = ConfigManager(str(config_file))
    assert new_manager.config.smart_mode is True
    assert new_manager.config.last_format == "MP3 Audio"
    assert new_manager.config.last_quality == "High"
