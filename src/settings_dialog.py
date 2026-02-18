import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QSpinBox, QComboBox, QCheckBox,
    QPushButton, QFileDialog, QFormLayout, QDialogButtonBox, QTimeEdit
)
from PyQt6.QtCore import Qt, QTime

class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Settings")
        self.setMinimumSize(450, 500)
        self.layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # General Tab
        self.tab_general = QWidget()
        gen_layout = QFormLayout(self.tab_general)
        self.download_path = QLineEdit()
        self.btn_browse = QPushButton("Browse")
        self.btn_browse.clicked.connect(self.select_folder)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.download_path)
        path_layout.addWidget(self.btn_browse)
        gen_layout.addRow("Download Folder:", path_layout)
        
        self.concurrent_downloads = QSpinBox()
        self.concurrent_downloads.setRange(1, 10)
        gen_layout.addRow("Max Concurrent Downloads:", self.concurrent_downloads)
        
        self.dark_mode = QCheckBox("Enable Dark Mode")
        gen_layout.addRow(self.dark_mode)

        # Formats Tab
        self.tab_formats = QWidget()
        fmt_layout = QFormLayout(self.tab_formats)
        self.pref_quality = QComboBox()
        self.pref_quality.addItems(["Best Available", "4K", "1080p", "720p"])
        fmt_layout.addRow("Preferred Quality:", self.pref_quality)
        self.video_codec = QComboBox()
        self.video_codec.addItems(["h264", "h265", "vp9", "av1"])
        fmt_layout.addRow("Video Codec:", self.video_codec)
        self.audio_codec = QComboBox()
        self.audio_codec.addItems(["mp3", "aac", "m4a", "opus"])
        fmt_layout.addRow("Audio Codec:", self.audio_codec)

        # Network Tab
        self.tab_network = QWidget()
        net_layout = QFormLayout(self.tab_network)
        self.proxy_url = QLineEdit()
        self.proxy_url.setPlaceholderText("http://user:pass@host:port")
        net_layout.addRow("Proxy URL:", self.proxy_url)
        self.socket_timeout = QSpinBox()
        self.socket_timeout.setRange(5, 300)
        net_layout.addRow("Socket Timeout (s):", self.socket_timeout)

        # Scheduler Tab
        self.tab_scheduler = QWidget()
        sch_layout = QFormLayout(self.tab_scheduler)
        self.sch_enabled = QCheckBox("Enable Download Scheduler")
        sch_layout.addRow(self.sch_enabled)
        
        self.sch_start = QTimeEdit()
        self.sch_start.setDisplayFormat("HH:mm")
        sch_layout.addRow("Start Time:", self.sch_start)
        
        self.sch_end = QTimeEdit()
        self.sch_end.setDisplayFormat("HH:mm")
        sch_layout.addRow("End Time:", self.sch_end)
        
        sch_info = QLabel("When enabled, new downloads will be queued until the start time.")
        sch_info.setWordWrap(True)
        sch_info.setStyleSheet("color: #8e8e93; font-size: 11px; margin-top: 10px;")
        sch_layout.addRow(sch_info)

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
        adv_layout.addRow("Archive File:", self.archive_path)
        
        self.browser_cookies = QComboBox()
        self.browser_cookies.addItems(["None", "chrome", "firefox", "edge", "opera", "safari"])
        adv_layout.addRow("Extract Browser Cookies:", self.browser_cookies)
        
        self.use_internal_browser = QCheckBox("Use Internal Browser Cookies")
        self.use_internal_browser.setToolTip("Uses cookies from the app's built-in browser tab.")
        adv_layout.addRow(self.use_internal_browser)

        # Experimental Tab
        self.tab_experimental = QWidget()
        exp_layout = QVBoxLayout(self.tab_experimental)
        
        warning_label = QLabel(
            "⚠️ LEGAL WARNING: Circumventing DRM (Digital Rights Management) "
            "may be illegal in your jurisdiction. This feature is for "
            "educational and backup purposes only. We do not condone piracy."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #ff9f0a; font-weight: bold; border: 1px solid #ff9f0a; padding: 10px; border-radius: 5px;")
        exp_layout.addWidget(warning_label)
        
        form_exp = QFormLayout()
        self.experimental_drm = QCheckBox("Enable Experimental Widevine Support")
        form_exp.addRow(self.experimental_drm)
        
        self.cdm_path = QLineEdit()
        cdm_row = QHBoxLayout()
        cdm_row.addWidget(self.cdm_path)
        self.btn_cdm = QPushButton("Browse")
        cdm_row.addWidget(self.btn_cdm)
        self.btn_cdm.clicked.connect(self.select_cdm)
        form_exp.addRow("CDM Device (.wvd):", cdm_row)
        
        exp_layout.addLayout(form_exp)
        exp_layout.addStretch()

        # Add tabs
        self.tabs.addTab(self.tab_general, "General")
        self.tabs.addTab(self.tab_formats, "Formats")
        self.tabs.addTab(self.tab_network, "Network")
        self.tabs.addTab(self.tab_scheduler, "Scheduler")
        self.tabs.addTab(self.tab_advanced, "Advanced")
        self.tabs.addTab(self.tab_experimental, "Experimental")
        
        self.layout.addWidget(self.tabs)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        
        self.load_settings()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder:
            self.download_path.setText(folder)

    def select_cookies(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Cookies File", "", "Text files (*.txt)")
        if file:
            self.cookies_path.setText(file)

    def select_cdm(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select CDM Device", "", "Widevine Device (*.wvd)")
        if file:
            self.cdm_path.setText(file)

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
        self.use_internal_browser.setChecked(config.use_internal_browser)
        self.experimental_drm.setChecked(config.experimental_drm)
        self.cdm_path.setText(config.cdm_path if config.cdm_path else "")
        
        # Scheduler
        self.sch_enabled.setChecked(config.scheduler_enabled)
        self.sch_start.setTime(QTime.fromString(config.scheduler_start, "HH:mm"))
        self.sch_end.setTime(QTime.fromString(config.scheduler_end, "HH:mm"))

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
            browser_cookies=self.browser_cookies.currentText(),
            use_internal_browser=self.use_internal_browser.isChecked(),
            experimental_drm=self.experimental_drm.isChecked(),
            cdm_path=self.cdm_path.text() if self.cdm_path.text() else None,
            scheduler_enabled=self.sch_enabled.isChecked(),
            scheduler_start=self.sch_start.time().toString("HH:mm"),
            scheduler_end=self.sch_end.time().toString("HH:mm")
        )
        self.accept()
