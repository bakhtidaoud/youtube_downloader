import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QSpinBox, QComboBox, QCheckBox,
    QPushButton, QFileDialog, QFormLayout, QDialogButtonBox, QTimeEdit
)
from PyQt6.QtCore import Qt, QTime

class SettingsDialog(QDialog):
    def __init__(self, config_manager, colors, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.colors = colors
        self.setWindowTitle("UltraTube Preferences")
        self.setMinimumSize(600, 650)
        self.apply_styles()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)
        
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.West) # Side tabs for modern look
        
        # --- General Tab ---
        self.tab_general = QWidget()
        gen_layout = QFormLayout(self.tab_general)
        gen_layout.setContentsMargins(20, 20, 20, 20)
        gen_layout.setSpacing(15)
        
        self.download_path = QLineEdit()
        self.btn_browse = QPushButton("Browse")
        self.btn_browse.clicked.connect(self.select_folder)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.download_path)
        path_layout.addWidget(self.btn_browse)
        gen_layout.addRow("Download Path:", path_layout)
        
        self.concurrent_downloads = QSpinBox()
        self.concurrent_downloads.setRange(1, 10)
        gen_layout.addRow("Max Threads:", self.concurrent_downloads)
        
        self.dark_mode = QCheckBox("Enable Deep Obsidian Theme")
        gen_layout.addRow(self.dark_mode)

        # --- Formats Tab ---
        self.tab_formats = QWidget()
        fmt_layout = QFormLayout(self.tab_formats)
        fmt_layout.setContentsMargins(20, 20, 20, 20)
        
        self.pref_quality = QComboBox()
        self.pref_quality.addItems(["Best Available", "4K", "1080p", "720p"])
        fmt_layout.addRow("Preferred Quality:", self.pref_quality)
        
        self.video_codec = QComboBox()
        self.video_codec.addItems(["h264", "h265", "vp9", "av1"])
        fmt_layout.addRow("Video Encoding:", self.video_codec)
        
        self.audio_codec = QComboBox()
        self.audio_codec.addItems(["mp3", "aac", "m4a", "opus"])
        fmt_layout.addRow("Audio Encoding:", self.audio_codec)

        # --- Scheduler Tab ---
        self.tab_scheduler = QWidget()
        sch_layout = QVBoxLayout(self.tab_scheduler)
        sch_layout.setContentsMargins(20, 20, 20, 20)
        
        self.sch_enabled = QCheckBox("Activate Smart Scheduler")
        self.sch_enabled.setStyleSheet("font-weight: bold; font-size: 14px;")
        sch_layout.addWidget(self.sch_enabled)
        
        sch_form = QFormLayout()
        self.sch_start = QTimeEdit()
        self.sch_start.setDisplayFormat("HH:mm")
        sch_form.addRow("Begin at:", self.sch_start)
        
        self.sch_end = QTimeEdit()
        self.sch_end.setDisplayFormat("HH:mm")
        sch_form.addRow("End at:", self.sch_end)
        sch_layout.addLayout(sch_form)
        
        sch_info = QLabel("Downloads added outside these hours will remain paused in the high-fidelity queue.")
        sch_info.setWordWrap(True)
        sch_info.setStyleSheet(f"color: {self.colors['sub_text']}; font-size: 12px; font-style: italic; margin-top: 10px;")
        sch_layout.addWidget(sch_info)
        sch_layout.addStretch()

        # Add tabs
        self.tabs.addTab(self.tab_general, "General")
        self.tabs.addTab(self.tab_formats, "Quality")
        self.tabs.addTab(self.tab_scheduler, "Scheduling")
        
        # --- Network Tab ---
        self.tab_network = QWidget()
        net_layout = QFormLayout(self.tab_network)
        net_layout.setContentsMargins(20, 20, 20, 20)
        net_layout.setSpacing(15)
        
        self.proxy_url = QLineEdit()
        self.proxy_url.setPlaceholderText("http://user:pass@host:port")
        net_layout.addRow("Proxy URL:", self.proxy_url)
        
        self.socket_timeout = QSpinBox()
        self.socket_timeout.setRange(10, 300)
        net_layout.addRow("Socket Timeout (s):", self.socket_timeout)
        
        self.browser_cookies = QComboBox()
        self.browser_cookies.addItems(["None", "chrome", "firefox", "edge", "safari", "opera", "vivaldi"])
        net_layout.addRow("Import Browser Cookies:", self.browser_cookies)
        
        self.cookies_path = QLineEdit()
        self.btn_cookies = QPushButton("Load .txt")
        self.btn_cookies.clicked.connect(self.select_cookies)
        ck_layout = QHBoxLayout()
        ck_layout.addWidget(self.cookies_path)
        ck_layout.addWidget(self.btn_cookies)
        net_layout.addRow("Cookies File:", ck_layout)

        # --- Advanced Tab ---
        self.tab_advanced = QWidget()
        adv_layout = QFormLayout(self.tab_advanced)
        adv_layout.setContentsMargins(20, 20, 20, 20)
        
        self.archive_path = QLineEdit()
        adv_layout.addRow("Download Archive:", self.archive_path)
        
        self.use_internal_browser = QCheckBox("Use Embedded Browser Engine")
        adv_layout.addRow(self.use_internal_browser)
        
        self.experimental_drm = QCheckBox("Enable Experimental DRM (CDM)")
        adv_layout.addRow(self.experimental_drm)
        
        self.cdm_path = QLineEdit()
        self.btn_cdm = QPushButton("Load .wvd")
        self.btn_cdm.clicked.connect(self.select_cdm)
        cdm_row = QHBoxLayout()
        cdm_row.addWidget(self.cdm_path)
        cdm_row.addWidget(self.btn_cdm)
        adv_layout.addRow("CDM Path:", cdm_row)

        # Add tabs
        self.tabs.addTab(self.tab_general, "General")
        self.tabs.addTab(self.tab_formats, "Quality")
        self.tabs.addTab(self.tab_scheduler, "Scheduling")
        self.tabs.addTab(self.tab_network, "Network")
        self.tabs.addTab(self.tab_advanced, "Advanced")
        
        self.layout.addWidget(self.tabs)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        
        self.load_settings()

    def apply_styles(self):
        accent = self.colors['accent']
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.colors['bg']}; }}
            QWidget {{ color: {self.colors['text']}; font-family: 'Inter', sans-serif; }}
            
            QTabWidget::pane {{ border: 1px solid {self.colors['border']}; border-radius: 12px; background: {self.colors['card']}; }}
            QTabBar::tab {{
                background: transparent;
                padding: 15px 20px;
                min-width: 120px;
                text-align: left;
                color: {self.colors['sub_text']};
            }}
            QTabBar::tab:selected {{
                color: {accent};
                font-weight: bold;
                border-right: 2px solid {accent};
            }}
            
            QLineEdit, QSpinBox, QComboBox, QTimeEdit {{
                background-color: {self.colors['bg']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 8px;
            }}
            
            QPushButton {{
                background-color: {self.colors['card']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{ border-color: {accent}; }}
        """)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder: self.download_path.setText(folder)

    def select_cookies(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Cookies File", "", "Text files (*.txt)")
        if file: self.cookies_path.setText(file)

    def select_cdm(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select CDM Device", "", "Widevine Device (*.wvd)")
        if file: self.cdm_path.setText(file)

    def load_settings(self):
        config = self.config_manager.config
        self.download_path.setText(config.download_folder)
        self.concurrent_downloads.setValue(config.max_concurrent)
        self.dark_mode.setChecked(config.dark_mode)
        
        def set_combo(combo, val):
            idx = combo.findText(val)
            if idx >= 0: combo.setCurrentIndex(idx)
        
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
        
        self.sch_enabled.setChecked(config.scheduler_enabled)
        self.sch_start.setTime(QTime.fromString(config.scheduler_start, "HH:mm"))
        self.sch_end.setTime(QTime.fromString(config.scheduler_end, "HH:mm"))

    def save_settings(self):
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
