import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QPushButton, QLabel, QLineEdit, QComboBox, QListWidget, 
    QListWidgetItem, QFrame, QProgressBar, QStackedWidget,
    QSystemTrayIcon, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, pyqtSlot, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QIcon

import downloader
from downloader import DownloadProgress
from src.config_manager import ConfigManager
from src.settings_dialog import SettingsDialog
from src.browser_tab import EmbeddedBrowser
from src.subscription_tab import SubscriptionTab

class DownloadWorker(QThread):
    progress_updated = pyqtSignal(object)
    finished = pyqtSignal(str)

    def __init__(self, url, format_id=None, settings=None):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.settings = settings or {}

    def run(self):
        def internal_callback(prog: DownloadProgress):
            self.progress_updated.emit(prog)

        downloader.download_item(
            self.url, 
            format_id=self.format_id,
            progress_callback=internal_callback,
            **self.settings
        )
        self.finished.emit("Complete")

class ModernDownloadItem(QFrame):
    remove_requested = pyqtSignal(object)
    finished_successfully = pyqtSignal(str)

    def __init__(self, url, colors):
        super().__init__()
        self.url = url
        self.colors = colors
        self.file_path = None
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(400)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        
        self.init_ui()
        self.fade_anim.start()

    def init_ui(self):
        self.setFixedHeight(110)
        self.update_style()
        
        layout = QVBoxLayout(self)
        top_row = QHBoxLayout()
        self.title_label = QLabel(self.url)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        top_row.addWidget(self.title_label, 1)

        self.btn_open = QPushButton("📂")
        self.btn_open.setFixedSize(30, 30)
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self.open_folder)
        top_row.addWidget(self.btn_open)

        self.btn_cancel = QPushButton("✕")
        self.btn_cancel.setFixedSize(30, 30)
        self.btn_cancel.clicked.connect(lambda: self.remove_requested.emit(self))
        top_row.addWidget(self.btn_cancel)
        layout.addLayout(top_row)

        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(6)
        self.pbar.setTextVisible(False)
        layout.addWidget(self.pbar)
        
        self.pbar_anim = QPropertyAnimation(self.pbar, b"value")
        self.pbar_anim.setDuration(400)
        self.pbar_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        bottom_row = QHBoxLayout()
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet(f"font-size: 11px; color: {self.colors['sub_text']};")
        bottom_row.addWidget(self.status_label)
        bottom_row.addStretch()
        self.stats_label = QLabel("- MB/s")
        self.stats_label.setStyleSheet(f"font-size: 11px; color: {self.colors['sub_text']}; font-family: 'Consolas';")
        bottom_row.addWidget(self.stats_label)
        layout.addLayout(bottom_row)

    def update_style(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card']};
                border-radius: 12px;
                padding: 10px;
                border: 1px solid {self.colors['border']};
            }}
            QLabel {{ color: {self.colors['text']}; border: none; }}
            QProgressBar {{ background-color: {self.colors['border']}; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {self.colors['accent']}; border-radius: 3px; }}
            QPushButton {{ background: transparent; color: {self.colors['text']}; border-radius: 5px; }}
            QPushButton:hover {{ background: {self.colors['border']}; }}
        """)

    @pyqtSlot(object)
    def update_progress(self, prog: DownloadProgress):
        if prog.status == 'downloading':
            self.title_label.setText(prog.title if len(prog.title) < 50 else prog.title[:47] + "...")
            target = int(prog.percentage)
            if target > self.pbar.value():
                self.pbar_anim.stop()
                self.pbar_anim.setEndValue(target)
                self.pbar_anim.start()
            self.status_label.setText(f"Downloading... {prog.percentage}%")
            self.stats_label.setText(f"{prog.speed} | {prog.eta}")
        elif prog.status == 'finished':
            self.pbar.setValue(100)
            self.status_label.setText("✅ Completed")
            self.btn_open.setEnabled(True)
            if prog.filename:
                self.file_path = prog.filename
                self.finished_successfully.emit(os.path.basename(prog.filename))

    def open_folder(self):
        folder = os.path.abspath("downloads")
        if sys.platform == 'win32': os.startfile(folder)
        else: subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open', folder])

class VideoDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.workers = {}
        self.setWindowTitle("UltraTube Premium")
        self.setMinimumSize(1000, 750)
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme("download-main"))
        self.tray_icon.show()

        self.init_theme()
        self.init_ui()
        self.init_smart_mode()

    def init_theme(self):
        is_dark = self.config_manager.config.dark_mode
        self.colors = {
            'bg': '#1c1c1e' if is_dark else '#f5f5f7',
            'card': '#2c2c2e' if is_dark else '#ffffff',
            'text': '#ffffff' if is_dark else '#1c1c1e',
            'sub_text': '#8e8e93',
            'border': '#3a3a3c' if is_dark else '#d1d1d6',
            'accent': '#0a84ff'
        }

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(70)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(5, 20, 5, 20)
        self.sidebar_layout.setSpacing(15)
        
        self.btn_nav_down = self.create_nav_btn("📥", 0)
        self.btn_nav_web = self.create_nav_btn("🌐", 1)
        self.btn_nav_sub = self.create_nav_btn("⭐", 2)
        
        self.sidebar_layout.addWidget(self.btn_nav_down)
        self.sidebar_layout.addWidget(self.btn_nav_web)
        self.sidebar_layout.addWidget(self.btn_nav_sub)
        self.sidebar_layout.addStretch()
        
        self.main_layout.addWidget(self.sidebar)

        # Stack
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        # Downloader View
        self.download_view = QWidget()
        dl_layout = QVBoxLayout(self.download_view)
        dl_layout.setContentsMargins(30, 30, 30, 30)
        dl_layout.setSpacing(20)

        # Header Row
        header_row = QHBoxLayout()
        title_vbox = QVBoxLayout()
        self.lbl_head = QLabel("UltraTube Downloader")
        self.lbl_head.setStyleSheet("font-size: 32px; font-weight: 800;")
        title_vbox.addWidget(self.lbl_head)
        self.lbl_sub = QLabel("Premium high-fidelity video extraction")
        self.lbl_sub.setStyleSheet(f"font-size: 14px; color: {self.colors['sub_text']};")
        title_vbox.addWidget(self.lbl_sub)
        header_row.addLayout(title_vbox)
        header_row.addStretch()
        
        self.btn_theme = QPushButton("🌓")
        self.btn_theme.setFixedSize(40, 40)
        self.btn_theme.clicked.connect(self.toggle_theme)
        header_row.addWidget(self.btn_theme)

        self.smart_btn = QPushButton("✨ Smart Mode")
        self.smart_btn.setFixedSize(140, 40)
        self.smart_btn.clicked.connect(self.toggle_smart_mode)
        header_row.addWidget(self.smart_btn)
        
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.clicked.connect(self.show_settings)
        header_row.addWidget(self.settings_btn)
        dl_layout.addLayout(header_row)

        # URL Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL here...")
        self.url_input.setFixedHeight(50)
        dl_layout.addWidget(self.url_input)

        # Options Row
        opt_row = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Best (Auto)", "MP4 Video", "MP3 Audio"])
        opt_row.addWidget(self.format_combo)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Maximum Quality", "1080p", "720p"])
        opt_row.addWidget(self.quality_combo)
        opt_row.addStretch()
        self.download_btn = QPushButton("Start Download")
        self.download_btn.setFixedSize(160, 45)
        self.download_btn.clicked.connect(self.start_new_download)
        opt_row.addWidget(self.download_btn)
        dl_layout.addLayout(opt_row)

        self.downloads_list = QListWidget()
        dl_layout.addWidget(self.downloads_list)
        
        self.stack.addWidget(self.download_view)
        self.stack.addWidget(EmbeddedBrowser())
        self.stack.addWidget(SubscriptionTab(self.config_manager))
        
        self.stack.currentChanged.connect(self.update_nav_styles)
        self.apply_styles()

    def create_nav_btn(self, icon, idx):
        btn = QPushButton(icon)
        btn.setFixedSize(60, 60)
        btn.clicked.connect(lambda: self.stack.setCurrentIndex(idx))
        return btn

    def apply_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {self.colors['bg']}; }}
            QWidget {{ color: {self.colors['text']}; font-family: 'Segoe UI'; }}
            QLineEdit {{ 
                background-color: {self.colors['card']}; 
                border: 1px solid {self.colors['border']}; 
                border-radius: 10px; padding: 10px; color: {self.colors['text']};
            }}
            QComboBox {{ 
                background-color: {self.colors['card']}; 
                border: 1px solid {self.colors['border']}; 
                border-radius: 8px; padding: 5px; color: {self.colors['text']};
            }}
            QPushButton {{
                background-color: {self.colors['card']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                color: {self.colors['text']};
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {self.colors['border']}; }}
            QListWidget {{ background: transparent; border: none; }}
        """)
        self.sidebar.setStyleSheet(f"background-color: {self.colors['bg']}; border-right: 1px solid {self.colors['border']};")
        self.download_btn.setStyleSheet(f"background-color: {self.colors['accent']}; color: white; border: none; border-radius: 10px;")
        self.update_nav_styles()

    def update_nav_styles(self):
        idx = self.stack.currentIndex()
        for i, btn in enumerate([self.btn_nav_down, self.btn_nav_web, self.btn_nav_sub]):
            btn.setStyleSheet(f"font-size: 24px; background: {self.colors['card'] if i==idx else 'transparent'}; border: none; border-radius: 12px;")

    def toggle_theme(self):
        self.config_manager.update(dark_mode=not self.config_manager.config.dark_mode)
        self.init_theme()
        self.apply_styles()

    def show_notification(self, title):
        self.tray_icon.showMessage("Download Finished", title, QSystemTrayIcon.MessageIcon.Information, 3000)

    def start_new_download(self):
        url = self.url_input.text().strip()
        if not url: return
        item = QListWidgetItem(self.downloads_list)
        widget = ModernDownloadItem(url, self.colors)
        widget.finished_successfully.connect(self.show_notification)
        item.setSizeHint(widget.sizeHint())
        self.downloads_list.addItem(item)
        self.downloads_list.setItemWidget(item, widget)
        
        config = self.config_manager.config
        settings = {
            'download_dir': config.download_folder, 'proxy': config.proxy,
            'cookie_file': config.cookies_file, 'internal_browser': config.use_internal_browser
        }
        worker = DownloadWorker(url, settings=settings)
        worker.progress_updated.connect(widget.update_progress)
        worker.start()
        self.url_input.clear()

    def init_smart_mode(self):
        self.update_smart_ui(self.config_manager.config.smart_mode)

    def toggle_smart_mode(self):
        new = not self.config_manager.config.smart_mode
        self.config_manager.update(smart_mode=new)
        self.update_smart_ui(new)

    def update_smart_ui(self, is_on):
        self.smart_btn.setText(f"✨ Smart: {'On' if is_on else 'Off'}")
        self.smart_btn.setStyleSheet(f"background-color: {self.colors['accent'] if is_on else self.colors['card']}; color: {'white' if is_on else self.colors['text']};")

    def show_settings(self):
        SettingsDialog(self.config_manager, self).exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = VideoDownloaderApp()
    window.show()
    sys.exit(app.exec())
