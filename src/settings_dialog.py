import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QSpinBox, QComboBox, QCheckBox,
    QPushButton, QFileDialog, QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("UltraTube - Preferences")
        self.setMinimumSize(500, 400)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # General Tab
        self.tab_general = QWidget()
        gen_layout = QFormLayout(self.tab_general)
        
        self.download_path = QLineEdit()
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.select_folder)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.download_path)
        path_layout.addWidget(self.browse_btn)
        gen_layout.addRow("Download Folder:", path_layout)
        
        self.concurrent_downloads = QSpinBox()
        self.concurrent_downloads.setRange(1, 10)
        gen_layout.addRow("Concurrent Downloads:", self.concurrent_downloads)
        
        self.dark_mode = QCheckBox("Enable Dark Mode (Restart required)")
        gen_layout.addRow(self.dark_mode)

        # Formats Tab
        self.tab_formats = QWidget()
        form_layout = QFormLayout(self.tab_formats)
        
        self.pref_quality = QComboBox()
        self.pref_quality.addItems(["best", "1080p", "720p", "480p", "worst"])
        form_layout.addRow("Preferred Quality:", self.pref_quality)
        
        self.video_codec = QComboBox()
        self.video_codec.addItems(["h264", "h265", "av1", "vp9"])
        form_layout.addRow("Preferred Video Codec:", self.video_codec)
        
        self.audio_codec = QComboBox()
        self.audio_codec.addItems(["mp3", "m4a", "wav", "flac"])
        form_layout.addRow("Preferred Audio Codec:", self.audio_codec)

        # Network Tab
        self.tab_network = QWidget()
        net_layout = QFormLayout(self.tab_network)
        
        self.proxy_url = QLineEdit()
        self.proxy_url.setPlaceholderText("http://user:password@host:port")
        net_layout.addRow("Proxy URL:", self.proxy_url)
        
        self.socket_timeout = QSpinBox()
        self.socket_timeout.setRange(5, 300)
        self.socket_timeout.setSuffix("s")
        net_layout.addRow("Socket Timeout:", self.socket_timeout)

        # Advanced Tab
        self.tab_advanced = QWidget()
        adv_layout = QFormLayout(self.tab_advanced)
        
        self.cookies_path = QLineEdit()
        self.cookies_btn = QPushButton("Select")
        self.cookies_btn.clicked.connect(self.select_cookies)
        cookies_layout = QHBoxLayout()
        cookies_layout.addWidget(self.cookies_path)
        cookies_layout.addWidget(self.cookies_btn)
        adv_layout.addRow("Cookies File:", cookies_layout)
        
        self.archive_path = QLineEdit()
        self.archive_path.setText("archive.txt")
        adv_layout.addRow("Archive File:", self.archive_path)
        
        self.browser_cookies = QComboBox()
        self.browser_cookies.addItems(["None", "chrome", "firefox", "edge", "opera", "safari"])
        adv_layout.addRow("Extract Browser Cookies:", self.browser_cookies)

        # Add tabs
        self.tabs.addTab(self.tab_general, "General")
        self.tabs.addTab(self.tab_formats, "Formats")
        self.tabs.addTab(self.tab_network, "Network")
        self.tabs.addTab(self.tab_advanced, "Advanced")
        
        self.layout.addWidget(self.tabs)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder:
            self.download_path.setText(folder)

    def select_cookies(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Cookies File", "", "Text files (*.txt)")
        if file:
            self.cookies_path.setText(file)

    def load_settings(self):
        config = self.config_manager.config
        self.download_path.setText(config.download_folder)
        self.concurrent_downloads.setValue(config.max_concurrent)
        self.dark_mode.setChecked(config.dark_mode)
        
        # Helper to set combo box index
        def set_combo(combo, val):
            index = combo.findText(val)
            if index >= 0: combo.setCurrentIndex(index)

        set_combo(self.pref_quality, config.preferred_quality)
        set_combo(self.video_codec, config.video_codec)
        set_combo(self.audio_codec, config.audio_codec)
        set_combo(self.browser_cookies, config.browser_cookies)
        
        self.proxy_url.setText(config.proxy if config.proxy else "")
        self.socket_timeout.setValue(config.socket_timeout)
        self.cookies_path.setText(config.cookies_file if config.cookies_file else "")
        self.archive_path.setText(config.archive_file)

    def save_settings(self):
        # Update config manager config object
        self.config_manager.update(
            download_folder=self.download_path.text(),
            max_concurrent=self.concurrent_downloads.value(),
            dark_mode=self.dark_mode.isChecked(),
            preferred_quality=self.pref_quality.currentText(),
            video_codec=self.video_codec.currentText(),
            audio_codec=self.audio_codec.currentText(),
            proxy=self.proxy_url.text() if self.proxy_url.text() else None,
            socket_timeout=self.socket_timeout.value(),
            cookies_file=self.cookies_path.text() if self.cookies_path.text() else None,
            archive_file=self.archive_path.text(),
            browser_cookies=self.browser_cookies.currentText()
        )
        self.accept()
