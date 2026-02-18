import json
import os
from dataclasses import dataclass, asdict, field
from typing import Optional

@dataclass
class AppConfig:
    download_folder: str = "downloads"
    preferred_quality: str = "best"
    proxy: Optional[str] = None
    dark_mode: bool = True
    auto_update_ytdlp: bool = True
    ffmpeg_path: Optional[str] = None

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load()

    def load(self) -> AppConfig:
        """Load settings from JSON file or return defaults if file doesn't exist."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return AppConfig(**data)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"Error loading config: {e}. Using defaults.")
        
        return AppConfig()

    def save(self, config: Optional[AppConfig] = None) -> None:
        """Save the current config to a JSON file."""
        if config:
            self.config = config
            
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def update(self, **kwargs) -> None:
        """Update specific settings and save immediately."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save()

# Example usage (can be removed or kept for testing)
if __name__ == "__main__":
    manager = ConfigManager()
    print(f"Initial folder: {manager.config.download_folder}")
    
    # Update a setting
    manager.update(download_folder="C:/Videos/Downloads", dark_mode=False)
    print(f"Updated folder: {manager.config.download_folder}")
